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

# Pop any stale cached version so we get the real module
sys.modules.pop("media_api", None)

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

# Restore managerurl to the original imported value
media_api.managerurl = "http://media-manager.test"

total = 14  # individual assertions across 7 test blocks
if failures > 0:
	print(f"\033[91m{failures} failures\033[0m in {total} assertions.")
	sys.exit(1)
else:
	print(f"All {total} fetchTrack assertions passed.")
