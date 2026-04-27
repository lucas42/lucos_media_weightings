#! /usr/bin/env python3
"""Unit tests for weight_track_controller in server.py.

Tests that the handler re-fetches track data from the event URL rather
than reading it directly from the event payload.

Run from src/ directory: python3 test_webhook.py
"""
import io
import json
import os
import sys
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
	body = json.dumps(body_dict).encode("utf-8")
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

# Test 1: handler fetches track from event["url"] and passes it to updateWeighting
with mock.patch.object(server, "fetchTrack", return_value=mock_track) as mock_fetch, \
     mock.patch.object(server, "updateWeighting", return_value="Weighting changed to 3.5") as mock_update:
	environ = make_environ({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	status, body = run_request(environ)
	test("returns 200 on success", status.startswith("200"))
	test("fetchTrack called with event url",
	     mock_fetch.call_args == mock.call("http://media.l42.eu/tracks/42"))
	test("updateWeighting called with fetched track",
	     mock_update.call_args == mock.call(mock_track))
	test("response body contains update message", "Weighting changed to 3.5" in body)

# Test 2: handler returns 400 when event has no "url" field
with mock.patch.object(server, "fetchTrack", return_value=mock_track), \
     mock.patch.object(server, "updateWeighting", return_value="ok"):
	environ = make_environ({"type": "trackAdded"})  # no url
	status, body = run_request(environ)
	test("missing url in event returns 400", status.startswith("400"))

# Test 3: fetchTrack failure returns 500
with mock.patch.object(server, "fetchTrack", side_effect=Exception("Connection failed")), \
     mock.patch.object(server, "updateWeighting", return_value="ok"):
	environ = make_environ({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	status, body = run_request(environ)
	test("fetchTrack failure returns 500", status.startswith("500"))

# Test 4: invalid JSON body returns 400
with mock.patch.object(server, "fetchTrack", return_value=mock_track), \
     mock.patch.object(server, "updateWeighting", return_value="ok"):
	bad_body = b"not valid json"
	bad_environ = {
		"REQUEST_METHOD": "POST",
		"PATH_INFO": "/weight-track",
		"CONTENT_LENGTH": str(len(bad_body)),
		"wsgi.input": io.BytesIO(bad_body),
	}
	status, body = run_request(bad_environ)
	test("invalid JSON body returns 400", status.startswith("400"))

# Test 5: updateWeighting failure returns 500
with mock.patch.object(server, "fetchTrack", return_value=mock_track), \
     mock.patch.object(server, "updateWeighting", side_effect=Exception("API error")):
	environ = make_environ({"type": "trackAdded", "url": "http://media.l42.eu/tracks/42"})
	status, body = run_request(environ)
	test("updateWeighting failure returns 500", status.startswith("500"))

# Test 6: fetchTrack raising ValueError (e.g. untrusted URL) returns 400
with mock.patch.object(server, "fetchTrack", side_effect=ValueError("URL must start with configured API")), \
     mock.patch.object(server, "updateWeighting", return_value="ok"):
	environ = make_environ({"type": "trackAdded", "url": "http://evil.example.com/tracks/42"})
	status, body = run_request(environ)
	test("disallowed URL (ValueError from fetchTrack) returns 400", status.startswith("400"))

total = 9  # individual assertions across 6 test blocks
if failures > 0:
	print(f"\033[91m{failures} failures\033[0m in {total} assertions.")
	sys.exit(1)
else:
	print(f"All {total} assertions passed.")
