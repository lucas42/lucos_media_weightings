#! /usr/local/bin/python3
import json, sys, os, time, traceback, queue, threading
from media_api import updateWeighting, fetchTrack
from waitress import serve

from health import probe_upstreams
from log_util import info, warn, error, debug

# Responses slower than this threshold are logged at WARN level so they can be
# grepped without trawling the full access log.  Format: "SLOW: POST /weight-track 200 1234ms"
SLOW_RESPONSE_THRESHOLD_MS = 1000

# How long (seconds) the queue can have depth > 0 without a successful event
# being processed before the drain-liveness check trips.  Must exceed the
# worst-case single-event processing time (one 30s-timeout-capped media-api
# call); 120s is comfortably above normal drain cadence (~3s/event) and still
# alerts within two monitor poll intervals.
DRAIN_LIVENESS_THRESHOLD_SECONDS = 120

# Unix timestamp of the last successful weighting update via the background worker.
# 0 means no successful update has happened since the process started.
_last_weighting_update = 0

# Total number of events that failed processing in the background worker since
# process start.  Kept as a metric and logged per-event for dashboard and log
# correlation; not used as a check determinant (see drain-liveness check).
_processing_failures = 0

# Bounded in-memory queue for async event processing.  A maxsize of 500 gives
# ~25 minutes of backlog capacity at the observed ~3s/event drain rate, which
# is comfortably above the largest burst we've seen (177 events, 2026-05-22).
_event_queue = queue.Queue(maxsize=500)

# Recorded at process start for the drain-liveness check: staleness is
# measured from max(last_weighting_update, process_start) so a fresh boot
# does not trip the check before the first event is processed.
_process_start_time = time.time()

# Module-level reference to the background worker thread.  Set in the
# __main__ block; remains None in test environments (worker never starts).
_worker_thread = None

if not os.environ.get("PORT"):
	error("PORT not set")
	sys.exit(1)
try:
	port = int(os.environ.get("PORT"))
except ValueError:
	error("PORT isn't an integer")
	sys.exit(1)

def _get_valid_keys():
	"""Parse CLIENT_KEYS env var (semicolon-separated name=value pairs) into a set of valid tokens."""
	client_keys_str = os.environ.get("CLIENT_KEYS", "")
	if not client_keys_str:
		return set()
	return {pair.split("=", 1)[1] for pair in client_keys_str.split(";") if "=" in pair}

def is_authorised(environ):
	"""Return True if the request has a valid Bearer token, or if CLIENT_KEYS is not configured."""
	valid_keys = _get_valid_keys()
	if not valid_keys:
		return True
	auth_header = environ.get("HTTP_AUTHORIZATION", "")
	if not auth_header.startswith("Bearer "):
		return False
	token = auth_header[len("Bearer "):]
	return token in valid_keys

def app(environ, start_response):
	"""WSGI entry point.

	Access log format: METHOD /path STATUS_CODE Xms
	  e.g.  POST /weight-track 202 1ms

	Lines at or above SLOW_RESPONSE_THRESHOLD_MS are prefixed "SLOW: " and
	emitted at WARN level so they can be grepped without scanning the full log.
	"""
	method = environ["REQUEST_METHOD"]
	path = environ["PATH_INFO"]
	start_time = time.time()

	# Wrap start_response so we can capture the status code for the access log.
	status_holder = [None]
	def logging_start_response(status, headers):
		status_holder[0] = status
		return start_response(status, headers)

	if method == "GET" and path == "/_info":
		result = info_controller(logging_start_response)
	elif method == "POST" and path == "/weight-track":
		result = weight_track_controller(environ, logging_start_response)
	else:
		logging_start_response("404 Not Found", [("Content-Type", "text/plain")])
		result = [b"Not Found"]

	elapsed_ms = int((time.time() - start_time) * 1000)
	status_code = status_holder[0].split(" ", 1)[0] if status_holder[0] else "???"
	log_line = f"{method} {path} {status_code} {elapsed_ms}ms"
	if elapsed_ms >= SLOW_RESPONSE_THRESHOLD_MS:
		warn(f"SLOW: {log_line}")
	elif path == "/_info":
		debug(log_line)
	else:
		info(log_line)
	return result

def info_controller(start_response):
	queue_depth = _event_queue.qsize()
	now = time.time()

	# Worker-alive: instant dead-thread detection.  A dead worker with an empty
	# queue is invisible to the drain-liveness check until the next event lands;
	# is_alive() catches it immediately.
	worker_alive_ok = _worker_thread is not None and _worker_thread.is_alive()

	# Drain-liveness: queue is non-empty AND no successful event has been
	# processed for DRAIN_LIVENESS_THRESHOLD_SECONDS.  Staleness is measured
	# from max(last_weighting_update, process_start) so a fresh boot does not
	# false-positive before the first event is processed.
	# - Covers a wedged/dead worker (depth climbs, success clock frozen) AND a
	#   hard-down downstream dependency.
	# - Self-heals the moment the queue drains or the success clock advances.
	# - Ignores single transient errors: one bad event doesn't create a sustained
	#   backlog with a frozen clock; the worker dequeues fast and moves on.
	reference_time = max(_last_weighting_update or 0, _process_start_time)
	staleness_seconds = now - reference_time
	drain_liveness_ok = not (queue_depth > 0 and staleness_seconds > DRAIN_LIVENESS_THRESHOLD_SECONDS)

	checks = probe_upstreams()
	checks["worker-alive"] = {
		"techDetail": (
			"Background worker thread is alive and able to process queued events. "
			"ok=False means no events can be processed — the queue will fill and "
			"/weight-track will return 503 Service Unavailable."
		),
		"ok": worker_alive_ok,
	}
	checks["drain-liveness"] = {
		"techDetail": (
			f"Queue is draining: ok=False when queue depth is non-zero and no successful event "
			f"has been processed for {DRAIN_LIVENESS_THRESHOLD_SECONDS}s "
			f"(staleness measured from max(last_weighting_update, process_start) to avoid fresh-boot false-positives). "
			f"Covers both a wedged worker and a hard-down downstream dependency. "
			f"Self-heals when the queue drains or a successful event advances the clock."
		),
		"ok": drain_liveness_ok,
	}

	metrics = {
		"last-weighting-update": {
			"value": _last_weighting_update,
			"techDetail": "Unix timestamp (seconds) of the most recent successful weighting update by the background worker since this process started. 0 means none yet — fresh boots will read 0 until the first webhook fires.",
		},
		"queue-depth": {
			"value": queue_depth,
			"techDetail": "Current number of events waiting in the internal queue for background processing. Non-zero during normal drain; sustained growth with a frozen last-weighting-update indicates a stall.",
		},
		"processing-failures": {
			"value": _processing_failures,
			"techDetail": "Total number of events the background worker failed to process since process start. Useful for dashboard trend and log correlation; each failure also emits an ERROR log line with the event URL.",
		},
	}
	output = {
		"system": "lucos_media_weightings",
		"ci": {
			"circle": "gh/lucas42/lucos_media_weightings",
		},
		"checks": checks,
		"metrics": metrics,
		"network_only": True,
		"show_on_homepage": False,
	}
	body = bytes(json.dumps(output, indent="\t") + "\n\n", "utf-8")
	start_response("200 OK", [("Content-Type", "application/json")])
	return [body]

def weight_track_controller(environ, start_response):
	"""Accept a webhook event for background processing.

	Validates auth and parses the JSON body synchronously, then immediately
	enqueues the event and returns 202 Accepted.  The actual work
	(fetchTrack + updateWeighting) happens in the background worker thread.

	This is the accept-202-enqueue pattern from ADR-0006.  The receive path
	is O(parse + enqueue) — sub-millisecond — regardless of downstream latency.
	"""
	if not is_authorised(environ):
		start_response("401 Unauthorized", [("Content-Type", "text/plain"), ("WWW-Authenticate", "Bearer")])
		return [b"Invalid API Key"]
	try:
		length = int(environ.get("CONTENT_LENGTH") or 0)
		post_data = environ["wsgi.input"].read(length)
		event = json.loads(post_data)
	except (ValueError, json.decoder.JSONDecodeError) as err:
		start_response("400 Bad Request", [("Content-Type", "text/plain")])
		return [bytes(str(err), "utf-8")]
	if "url" not in event:
		start_response("400 Bad Request", [("Content-Type", "text/plain")])
		return [b"Missing 'url' field in event"]
	try:
		_event_queue.put_nowait(event)
	except queue.Full:
		warn(f"Event queue full (depth={_event_queue.qsize()}), dropping event for {event.get('url', '?')}")
		start_response("503 Service Unavailable", [("Content-Type", "text/plain")])
		return [b"Queue full, retry later"]
	start_response("202 Accepted", [("Content-Type", "text/plain")])
	return [b"Accepted"]

def _process_event(event):
	"""Process a single queued event: fetch the current track state then update its weighting.

	Called by the background worker thread.  Updates _last_weighting_update on
	success; increments _processing_failures on any exception (and logs an error
	line with the event URL for log correlation).
	"""
	global _last_weighting_update, _processing_failures
	try:
		track = fetchTrack(event["url"])
		response = updateWeighting(track)
		_last_weighting_update = int(time.time())
		info(f"Processed weighting update for {event['url']}: {response}")
	except Exception as err:
		traceback.print_exc()
		error(f"Error processing event for {event.get('url', '?')}: {str(err)}")
		_processing_failures += 1

def _worker():
	"""Background daemon thread that drains _event_queue one event at a time."""
	while True:
		event = _event_queue.get()
		_process_event(event)
		_event_queue.task_done()

if __name__ == "__main__":
	_worker_thread = threading.Thread(target=_worker, daemon=True, name="event-queue-worker")
	_worker_thread.start()
	info("Server started on port %s" % (port))
	serve(app, host="0.0.0.0", port=port)
