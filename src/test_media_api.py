#! /usr/bin/env python3
"""Unit tests for fetchTrack() in src/media_api.py.

Tests the SSRF guard and cross-domain redirect handling introduced in
PRs #189 and #196.

Run from src/ directory: python3 test_media_api.py
"""
import os
import sys
import unittest.mock as mock
from unittest.mock import MagicMock

# Set required env vars before importing media_api.py to avoid module-level exits
os.environ["MEDIA_API"] = "http://media-api.test"
os.environ["KEY_LUCOS_MEDIA_METADATA_API"] = "test-api-key"
os.environ["MEDIA_METADATA_MANAGER_ORIGIN"] = "http://media-manager.test"
os.environ.setdefault("TIME_API", "http://stub")

# Stub the `requests` module before any imports that need it.
# media_api.py and time_api.py both do `import requests`, but `requests` is a
# pipenv dependency not available to the system python3 used by CI.
# The same approach is used by test_auth.py and test_webhook.py for their deps.
import types
_requests_stub = types.ModuleType("requests")
sys.modules.setdefault("requests", _requests_stub)

# Pop any stale cached versions so they re-import with our stub
sys.modules.pop("media_api", None)
sys.modules.pop("time_api", None)

import media_api
from media_api import fetchTrack

failures = 0

def test(comment, passed):
	global failures
	if not passed:
		print(f"\033[91mFailed\033[0m {comment}")
		failures += 1

def make_response(is_redirect=False, location=None, json_data=None, url="http://media-api.test/tracks/1", raise_error=None):
	"""Build a minimal mock HTTP response."""
	resp = MagicMock()
	resp.is_redirect = is_redirect
	resp.is_permanent_redirect = False
	resp.url = url
	resp.headers = {"Location": location} if location else {}
	if json_data is not None:
		resp.json.return_value = json_data
	if raise_error:
		resp.raise_for_status.side_effect = raise_error
	else:
		resp.raise_for_status.return_value = None
	return resp

mock_track = {"id": 42, "tags": {"title": [{"name": "Test Track"}]}, "collections": []}

# --- Test 1: Direct MEDIA_API URL → no redirect → returns JSON ---
media_api.managerurl = ""  # no manager configured for this test
api_resp = make_response(json_data=mock_track, url="http://media-api.test/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.return_value = api_resp
	result = fetchTrack("http://media-api.test/tracks/42")
	call_headers = mock_requests.get.call_args[1]['headers']
	test("direct MEDIA_API URL returns parsed JSON", result == mock_track)
	test("Accept: application/json sent", call_headers['Accept'] == 'application/json')
	test("Authorization: Bearer sent", call_headers['Authorization'] == 'Bearer test-api-key')
	test("only one HTTP request made (no redirect path)", mock_requests.get.call_count == 1)

# --- Test 2: MEDIA_API URL → 302 to another MEDIA_API URL → follows redirect ---
media_api.managerurl = ""
redirect_resp = make_response(is_redirect=True, location="http://media-api.test/v3/tracks/42", url="http://media-api.test/tracks/42")
api_resp2 = make_response(json_data=mock_track, url="http://media-api.test/v3/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.side_effect = [redirect_resp, api_resp2]
	result = fetchTrack("http://media-api.test/tracks/42")
	second_call_headers = mock_requests.get.call_args_list[1][1]['headers']
	test("MEDIA_API redirect followed and returns JSON", result == mock_track)
	test("Authorization re-sent on redirect", second_call_headers['Authorization'] == 'Bearer test-api-key')

# --- Test 3: MEDIA_MANAGER URL → 302 to MEDIA_API URL → follows with Authorization ---
media_api.managerurl = "http://media-manager.test"
manager_redirect = make_response(is_redirect=True, location="http://media-api.test/v3/tracks/42", url="http://media-manager.test/tracks/42")
api_resp3 = make_response(json_data=mock_track, url="http://media-api.test/v3/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.side_effect = [manager_redirect, api_resp3]
	result = fetchTrack("http://media-manager.test/tracks/42")
	first_call_headers = mock_requests.get.call_args_list[0][1]['headers']
	second_call_headers = mock_requests.get.call_args_list[1][1]['headers']
	test("MEDIA_MANAGER redirect to MEDIA_API returns JSON", result == mock_track)
	test("Accept: application/json sent on initial manager request", first_call_headers['Accept'] == 'application/json')
	test("Authorization re-sent on cross-domain redirect to API", second_call_headers['Authorization'] == 'Bearer test-api-key')

# --- Test 4: MEDIA_MANAGER URL → 302 to non-MEDIA_API target → raises ValueError ---
media_api.managerurl = "http://media-manager.test"
untrusted_redirect = make_response(is_redirect=True, location="http://evil.example.com/tracks/42", url="http://media-manager.test/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.return_value = untrusted_redirect
	raised = False
	try:
		fetchTrack("http://media-manager.test/tracks/42")
	except ValueError:
		raised = True
	test("untrusted redirect target raises ValueError", raised)

# --- Test 5: Unrecognised URL → raises ValueError without making HTTP request ---
media_api.managerurl = "http://media-manager.test"
with mock.patch.object(media_api, 'requests') as mock_requests:
	raised = False
	try:
		fetchTrack("http://evil.example.com/tracks/42")
	except ValueError:
		raised = True
	test("unrecognised URL raises ValueError", raised)
	test("no HTTP request made for unrecognised URL", mock_requests.get.call_count == 0)

# --- Test 6: MEDIA_METADATA_MANAGER_ORIGIN not set → manager URL rejected ---
media_api.managerurl = ""  # simulate env var not set
with mock.patch.object(media_api, 'requests') as mock_requests:
	raised = False
	try:
		fetchTrack("http://media-manager.test/tracks/42")
	except ValueError:
		raised = True
	test("manager URL rejected when MEDIA_METADATA_MANAGER_ORIGIN not set", raised)

# --- Test 7: HTTP error from final response → propagates ---
media_api.managerurl = ""
error_resp = make_response(raise_error=Exception("503 Service Unavailable"), url="http://media-api.test/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.return_value = error_resp
	raised = False
	try:
		fetchTrack("http://media-api.test/tracks/42")
	except Exception:
		raised = True
	test("HTTP error from raise_for_status propagates", raised)

# --- Test 8: MEDIA_MANAGER URL → 200 with JSON directly → returns JSON, no redirect ---
# Documents the non-redirect manager path: if the manager ever supports JSON
# content negotiation directly (it doesn't today, but a future rewrite might),
# fetchTrack must handle it correctly without invoking the redirect block.
media_api.managerurl = "http://media-manager.test"
manager_direct_resp = make_response(json_data=mock_track, url="http://media-manager.test/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.return_value = manager_direct_resp
	result = fetchTrack("http://media-manager.test/tracks/42")
	call_headers = mock_requests.get.call_args[1]['headers']
	test("MEDIA_MANAGER URL with direct 200 JSON response returns parsed JSON", result == mock_track)
	test("only one HTTP request made when manager returns 200 directly", mock_requests.get.call_count == 1)
	test("Authorization sent on direct manager request", call_headers['Authorization'] == 'Bearer test-api-key')

# --- Test 9: Production failure mode — manager redirects to auth service (issue #195) ---
# In production, https://media-metadata.l42.eu/tracks/N returns 302 to
# https://auth.l42.eu/authenticate?redirect_uri=... because the manager UI
# uses session-based auth via auth.l42.eu and does not honour Bearer tokens.
# fetchTrack must reject this with ValueError so the webhook handler returns
# 400 cleanly. This is the exact failure that broke webhooks for ~45 minutes
# on 2026-04-27 between v1.0.28 and v1.0.30; the redirect-following fix in
# PR #196 turned out not to work because the manager doesn't redirect to the
# API at all — it redirects to a third-party auth service.
media_api.managerurl = "http://media-manager.test"
auth_redirect = make_response(
	is_redirect=True,
	location="http://auth.test/authenticate?redirect_uri=http%3A%2F%2Fmedia-manager.test%2Ftracks%2F42",
	url="http://media-manager.test/tracks/42",
)
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.return_value = auth_redirect
	raised = False
	try:
		fetchTrack("http://media-manager.test/tracks/42")
	except ValueError:
		raised = True
	test("manager-redirect-to-auth-service raises ValueError (production failure mode #195)", raised)

# --- Test 10: 302 with missing Location header → ValueError (not KeyError) ---
media_api.managerurl = "http://media-manager.test"
redirect_no_location = make_response(is_redirect=True, location=None, url="http://media-manager.test/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.return_value = redirect_no_location
	raised = False
	try:
		fetchTrack("http://media-manager.test/tracks/42")
	except ValueError:
		raised = True
	test("302 with missing Location header raises ValueError (not KeyError)", raised)

# --- Test 11: second call returns 302 → ValueError (multi-hop bypass prevented) ---
media_api.managerurl = ""
first_redirect = make_response(is_redirect=True, location="http://media-api.test/v3/tracks/42", url="http://media-api.test/tracks/42")
second_redirect = make_response(is_redirect=True, location="http://evil.example.com/data", url="http://media-api.test/v3/tracks/42")
with mock.patch.object(media_api, 'requests') as mock_requests:
	mock_requests.get.side_effect = [first_redirect, second_redirect]
	raised = False
	try:
		fetchTrack("http://media-api.test/tracks/42")
	except ValueError:
		raised = True
	test("second redirect from API raises ValueError (multi-hop bypass prevented)", raised)

# Restore managerurl to the original imported value
media_api.managerurl = "http://media-manager.test"

total = 20  # individual assertions across 11 test blocks
if failures > 0:
	print(f"\033[91m{failures} failures\033[0m in {total} assertions.")
	sys.exit(1)
else:
	print(f"All {total} fetchTrack assertions passed.")
