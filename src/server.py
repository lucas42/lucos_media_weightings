#! /usr/local/bin/python3
import json, sys, os, time, traceback
from media_api import updateWeighting, fetchTrack
from waitress import serve

from health import probe_upstreams
from log_util import info, warn, error

# Responses slower than this threshold are logged at WARN level so they can be
# grepped without trawling the full access log.  Format: "SLOW: POST /weight-track 200 1234ms"
SLOW_RESPONSE_THRESHOLD_MS = 1000

# Unix timestamp of the last successful weighting update via /weight-track.
# 0 means no successful update has happened since the process started.
_last_weighting_update = 0

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
	  e.g.  POST /weight-track 200 42ms

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
	else:
		info(log_line)
	return result

def info_controller(start_response):
	metrics = {
		"last-weighting-update": {
			"value": _last_weighting_update,
			"techDetail": "Unix timestamp (seconds) of the most recent successful /weight-track call since this process started. 0 means none yet — fresh boots will read 0 until the first webhook fires.",
		},
	}
	output = {
		"system": "lucos_media_weightings",
		"ci": {
			"circle": "gh/lucas42/lucos_media_weightings",
		},
		"checks": probe_upstreams(),
		"metrics": metrics,
		"network_only": True,
		"show_on_homepage": False,
	}
	body = bytes(json.dumps(output, indent="\t") + "\n\n", "utf-8")
	start_response("200 OK", [("Content-Type", "application/json")])
	return [body]

def weight_track_controller(environ, start_response):
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
		track = fetchTrack(event["url"])
		response = updateWeighting(track)
		global _last_weighting_update
		_last_weighting_update = int(time.time())
		start_response("200 OK", [("Content-Type", "text/plain")])
		return [bytes(response, "utf-8")]
	except ValueError as err:
		start_response("400 Bad Request", [("Content-Type", "text/plain")])
		return [bytes(str(err), "utf-8")]
	except Exception as err:
		traceback.print_exc()
		error(f"Error updating weighting: {str(err)}")
		start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
		return [bytes(str(err), "utf-8")]

if __name__ == "__main__":
	info("Server started on port %s" % (port))
	serve(app, host="0.0.0.0", port=port)
