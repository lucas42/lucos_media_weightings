#! /usr/bin/env python3
"""Unit tests for weight_track_controller, _process_event, and /_info checks in server.py.

The webhook handler follows the accept-202-enqueue pattern (ADR-0006):
- HTTP path: validate auth + parse JSON, enqueue event, return 202 immediately.
- Background worker: calls _process_event per event (fetchTrack + updateWeighting).
- /_info: worker-alive and drain-liveness checks surface queue health to monitoring.

Run from src/ directory: python3 test_webhook.py
"""
import io
import json as _json
import os
import queue
import sys
import time
import types
import unittest.mock as mock

# Set required env vars before importing server.py to avoid module-level exits
os.environ.setdefault("PORT", "8080")
os.environ.setdefault("TIME_API", "http://stub")

# Pop any cached server module from a previous test run in the same process
sys.modules.pop("server", None)

# Stub out all non-stdlib modules server.py imports
_STUB_MOD_NAMES = ("media_api", "schedule_tracker", "time_api", "loganne", "waitress")
for mod_name in _STUB_MOD_NAMES:
	stub = types.ModuleType(mod_name)
	stub.updateWeighting = None  # satisfy 'from media_api import updateWeighting'
	stub.fetchTrack = None  # satisfy 'from media_api import fetchTrack'
	stub.serve = lambda *a, **kw: None  # satisfy 'from waitress import serve'
	sys.modules[mod_name] = stub

import server

# Pop stubs so other test files can import the real modules if needed
for mod_name in _STUB_MOD_NAMES:
	sys.modules.pop(mod_name, None)

failures = 0

def make_environ(body_dict):
	"""Build a minimal WSGI environ for a POST /weight-track request."""
	body = _json.dumps(body_dict).encode("utf-8")
	return {
		"REQUEST_METHOD": "POST",
		"PATH_INFO": "/weight-track",
		"CONTENT_LENGTH": str(len(body)),
		"wsgi.input": io.BytesIO(body),
	}

def run_request(environ):
	"""Run the WSGI app and return (status, response_body)."""
	status_holder = [None]
	def start_response(status, headers):
		status_holder[0] = status
	body = b"".join(server.app(environ, start_response))
	return status_holder[0], body.decode("utf-8")

def run_info():
	"""Run a GET /_info request and return the parsed JSON body."""
	environ = {
		"REQUEST_METHOD": "GET",
		"PATH_INFO": "/_info",
		"CONTENT_LENGTH": "0",
		"wsgi.input": io.BytesIO(b""),
	}
	_, body = run_request(environ)
	return _json.loads(body)

def test(comment, passed):
	global failures
	if not passed:
		print(f"\033[91mFailed\033[0m {comment}")
		failures += 1

# Clear CLIENT_KEYS so all requests are authorised by default
os.environ.pop("CLIENT_KEYS", None)

mock_track = {
	"id": 42,
	"tags": {"title": [{"name": "Test Track"}]},
	"collections": [],
}

# --- HTTP-layer tests: enqueue and return 202 ---

# Test 1: valid event returns 202 and event is enqueued
with mock.patch.object(server._event_queue, "put_nowait") as mock_put:
	environ = make_environ({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	status, body = run_request(environ)
	test("returns 202 Accepted on valid event", status.startswith("202"))
	test("event enqueued with correct url",
	     mock_put.call_args == mock.call({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"}))

# Test 2: valid event — fetchTrack and updateWeighting are NOT called synchronously
with mock.patch.object(server._event_queue, "put_nowait"), \
     mock.patch.object(server, "fetchTrack") as mock_fetch, \
     mock.patch.object(server, "updateWeighting") as mock_update:
	environ = make_environ({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	run_request(environ)
	test("fetchTrack not called synchronously on request path", not mock_fetch.called)
	test("updateWeighting not called synchronously on request path", not mock_update.called)

# Test 3: missing 'url' field in event returns 400
with mock.patch.object(server._event_queue, "put_nowait"):
	environ = make_environ({"type": "trackAdded"})  # no url field
	status, body = run_request(environ)
	test("missing url in event returns 400", status.startswith("400"))

# Test 4: invalid JSON body returns 400
bad_body = b"not valid json"
bad_environ = {
	"REQUEST_METHOD": "POST",
	"PATH_INFO": "/weight-track",
	"CONTENT_LENGTH": str(len(bad_body)),
	"wsgi.input": io.BytesIO(bad_body),
}
status, body = run_request(bad_environ)
test("invalid JSON body returns 400", status.startswith("400"))

# Test 5: queue full returns 503
with mock.patch.object(server._event_queue, "put_nowait", side_effect=queue.Full):
	environ = make_environ({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	status, body = run_request(environ)
	test("queue full returns 503", status.startswith("503"))

# --- _process_event tests ---

# Test 6: success path — fetchTrack called with event url, updateWeighting called with track
server._last_weighting_update = 0
with mock.patch.object(server, "fetchTrack", return_value=mock_track) as mock_fetch, \
     mock.patch.object(server, "updateWeighting", return_value="Weighting changed to 3.5") as mock_update:
	server._process_event({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	test("_process_event calls fetchTrack with event url",
	     mock_fetch.call_args == mock.call("http://media.l42.eu/tracks/42"))
	test("_process_event calls updateWeighting with fetched track",
	     mock_update.call_args == mock.call(mock_track))
	test("_process_event updates _last_weighting_update on success",
	     server._last_weighting_update > 0)

# Test 7: fetchTrack failure increments _processing_failures
server._processing_failures = 0
with mock.patch.object(server, "fetchTrack", side_effect=Exception("Connection failed")), \
     mock.patch.object(server, "updateWeighting", return_value="ok"):
	server._process_event({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	test("fetchTrack failure increments _processing_failures", server._processing_failures == 1)

# Test 8: updateWeighting failure increments _processing_failures
server._processing_failures = 0
with mock.patch.object(server, "fetchTrack", return_value=mock_track), \
     mock.patch.object(server, "updateWeighting", side_effect=Exception("API error")):
	server._process_event({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	test("updateWeighting failure increments _processing_failures", server._processing_failures == 1)

# Test 9: ValueError from fetchTrack (disallowed URL) increments _processing_failures
server._processing_failures = 0
with mock.patch.object(server, "fetchTrack", side_effect=ValueError("URL must start with configured API")), \
     mock.patch.object(server, "updateWeighting", return_value="ok"):
	server._process_event({"type": "trackAdded", "url": "http://evil.example.com/tracks/42"})
	test("ValueError from fetchTrack increments _processing_failures", server._processing_failures == 1)

# --- /_info check tests: drain-liveness and worker-alive ---

# Shared helper: run /_info with probe_upstreams stubbed out and a mock worker thread.
def _run_info_with(*, qsize, last_success, process_start, worker_alive=True):
	mock_thread = mock.MagicMock()
	mock_thread.is_alive.return_value = worker_alive
	orig_process_start = server._process_start_time
	orig_last_success = server._last_weighting_update
	server._process_start_time = process_start
	server._last_weighting_update = last_success
	try:
		with mock.patch.object(server, "_worker_thread", mock_thread), \
		     mock.patch.object(server._event_queue, "qsize", return_value=qsize), \
		     mock.patch.object(server, "probe_upstreams", return_value={}), \
		     mock.patch.object(server, "debug"):
			return run_info()
	finally:
		server._process_start_time = orig_process_start
		server._last_weighting_update = orig_last_success

now = time.time()

# Test 10: drain-liveness ok=False when queue non-empty and stale
data = _run_info_with(
	qsize=5,
	last_success=0,  # no success yet
	process_start=now - (server.DRAIN_LIVENESS_THRESHOLD_SECONDS + 60),  # well past threshold
)
test("drain-liveness ok=False when queue non-empty and stale",
     data["checks"]["drain-liveness"]["ok"] is False)

# Test 11: drain-liveness ok=True when queue empty (even if stale — no backlog to drain)
data = _run_info_with(
	qsize=0,
	last_success=0,
	process_start=now - (server.DRAIN_LIVENESS_THRESHOLD_SECONDS + 60),
)
test("drain-liveness ok=True when queue empty",
     data["checks"]["drain-liveness"]["ok"] is True)

# Test 12: drain-liveness ok=True when queue non-empty but recent success (active drain)
data = _run_info_with(
	qsize=10,
	last_success=int(now) - 5,  # success 5 seconds ago, well within threshold
	process_start=now - 300,
)
test("drain-liveness ok=True when queue non-empty but success is recent",
     data["checks"]["drain-liveness"]["ok"] is True)

# Test 13: drain-liveness ok=True within fresh-boot window even with no success yet
data = _run_info_with(
	qsize=5,
	last_success=0,  # no success yet
	process_start=now - 10,  # only 10s old — within threshold
)
test("drain-liveness ok=True within fresh-boot window (process_start used as reference)",
     data["checks"]["drain-liveness"]["ok"] is True)

# Test 14: worker-alive ok=True when thread is alive
data = _run_info_with(qsize=0, last_success=0, process_start=now, worker_alive=True)
test("worker-alive ok=True when thread is alive",
     data["checks"]["worker-alive"]["ok"] is True)

# Test 15: worker-alive ok=False when _worker_thread is None
orig_thread = server._worker_thread
server._worker_thread = None
with mock.patch.object(server._event_queue, "qsize", return_value=0), \
     mock.patch.object(server, "probe_upstreams", return_value={}), \
     mock.patch.object(server, "debug"):
	data = run_info()
test("worker-alive ok=False when _worker_thread is None",
     data["checks"]["worker-alive"]["ok"] is False)
server._worker_thread = orig_thread

# --- Access log tests ---

# Test 16: access log includes status code and response time on a successful POST
with mock.patch.object(server._event_queue, "put_nowait"), \
     mock.patch.object(server, "info") as mock_info:
	environ = make_environ({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	run_request(environ)
	log_lines = [call[0][0] for call in mock_info.call_args_list]
	access_log = next((l for l in log_lines if "/weight-track" in l), "")
	test("access log includes 202 status code", "202" in access_log)
	test("access log includes response time in ms", "ms" in access_log)

# Test 17: /_info access log uses debug level, not info level
with mock.patch.object(server, "debug") as mock_debug, \
     mock.patch.object(server, "info") as mock_info, \
     mock.patch.object(server, "probe_upstreams", return_value={}):
	info_environ = {
		"REQUEST_METHOD": "GET",
		"PATH_INFO": "/_info",
		"CONTENT_LENGTH": "0",
		"wsgi.input": io.BytesIO(b""),
	}
	run_request(info_environ)
	debug_lines = [call[0][0] for call in mock_debug.call_args_list]
	info_lines = [call[0][0] for call in mock_info.call_args_list]
	access_debug = next((l for l in debug_lines if "/_info" in l), "")
	access_info = next((l for l in info_lines if "/_info" in l), "")
	test("/_info access log uses debug level", "/_info" in access_debug)
	test("/_info access log does not use info level", access_info == "")

total = 24  # individual assertions across 17 test blocks
if failures > 0:
	print(f"\033[91m{failures} failures\033[0m in {total} assertions.")
	sys.exit(1)
else:
	print(f"All {total} assertions passed.")
