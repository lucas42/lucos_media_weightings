#! /usr/bin/env python3
"""Unit tests for all-tracks.py.

Two suites:

1. Mock-loganne suite (fast path) — stubs the whole loganne module and verifies
   the Python call args: type='weightings', level='detail'.

2. Real-transport suite — uses the real v2 loganne client but patches its HTTP
   session so no network call is made. Verifies the HTTP POST body contains the
   required fields. A broken level (missing or invalid) would fail here because
   the v2 client raises ValueError before even reaching the network.

Run from src/ directory: python3 test_all_tracks.py
"""
import importlib.util
import os
import pathlib
import sys
import types
import unittest.mock as mock

# Set required env vars before the script's module-level code runs
os.environ.setdefault("SYSTEM", "lucos_media_weightings")
os.environ.setdefault("LOGANNE_ENDPOINT", "http://stub-loganne/events")
os.environ.setdefault("MEDIA_API", "http://stub-media")
os.environ.setdefault("TIME_API", "http://stub-time")

_script_path = pathlib.Path(__file__).parent / "all-tracks.py"

# ---------------------------------------------------------------------------
# Suite 1: mock-loganne — verify Python call args
# ---------------------------------------------------------------------------

mock_update_loganne = mock.Mock()
mock_update_schedule_tracker = mock.Mock()

_STUB_MOD_NAMES = ("media_api", "time_api", "loganne", "schedule_tracker", "log_util")
for mod_name in _STUB_MOD_NAMES:
    stub = types.ModuleType(mod_name)
    stub.getAllTracks = lambda: []           # no tracks — skip the main loop
    stub.updateWeighting = lambda track, **kw: "Weighting stayed the same"
    stub.getCurrentItems = lambda: []
    stub.updateLoganne = mock_update_loganne
    stub.updateScheduleTracker = mock_update_schedule_tracker
    stub.info = lambda *a: None
    stub.error = lambda *a: None
    sys.modules[mod_name] = stub

# Execute the script (name contains a hyphen so importlib is needed)
spec = importlib.util.spec_from_file_location("all_tracks", _script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Clean up stubs so the real-transport suite can import the real loganne
for mod_name in _STUB_MOD_NAMES:
    sys.modules.pop(mod_name, None)

failures = 0

def test(comment, passed):
    global failures
    if not passed:
        print(f"\033[91mFailed\033[0m {comment}")
        failures += 1

# Verify the loganne call was made with the right arguments
test("updateLoganne called at least once", mock_update_loganne.call_count >= 1)

weightings_calls = [
    c for c in mock_update_loganne.call_args_list
    if c.kwargs.get("type") == "weightings"
]
test("updateLoganne called with type='weightings'", len(weightings_calls) >= 1)
test(
    "updateLoganne called with level='detail'",
    any(c.kwargs.get("level") == "detail" for c in weightings_calls),
)

# ---------------------------------------------------------------------------
# Suite 2: real-transport — drive the real v2 client against a stubbed HTTP
# session.  A missing or invalid level raises ValueError in the client before
# any network call, so this test would catch a future signature regression.
# ---------------------------------------------------------------------------

# Import the real loganne module (not the stub from suite 1).
# The module was popped from sys.modules above, so this is a fresh import.
import loganne as _real_loganne  # noqa: E402

captured_payloads = []

def _fake_post(url, **kwargs):
    captured_payloads.append({"url": url, "json": kwargs.get("json", {})})
    resp = mock.MagicMock()
    resp.raise_for_status = lambda: None
    return resp

# Stub every module except loganne so the script runs without real network calls
_STUB_MOD_NAMES_REAL = ("media_api", "time_api", "schedule_tracker", "log_util")
for mod_name in _STUB_MOD_NAMES_REAL:
    stub = types.ModuleType(mod_name)
    stub.getAllTracks = lambda: []
    stub.updateWeighting = lambda track, **kw: "Weighting stayed the same"
    stub.getCurrentItems = lambda: []
    stub.updateScheduleTracker = lambda **kw: None
    stub.info = lambda *a: None
    stub.error = lambda *a: None
    sys.modules[mod_name] = stub

# Run the script with the real loganne but intercepted HTTP transport
with mock.patch.object(_real_loganne.session, "post", side_effect=_fake_post):
    spec2 = importlib.util.spec_from_file_location("all_tracks_real", _script_path)
    module2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(module2)

# Clean up
for mod_name in _STUB_MOD_NAMES_REAL:
    sys.modules.pop(mod_name, None)

weightings_http = [
    p for p in captured_payloads
    if p["json"].get("type") == "weightings"
]

test(
    "real loganne client POSTed to LOGANNE_ENDPOINT",
    any(p["url"] == os.environ["LOGANNE_ENDPOINT"] for p in captured_payloads),
)
test(
    "real loganne HTTP payload includes level='detail'",
    any(p["json"].get("level") == "detail" for p in weightings_http),
)
test(
    "real loganne HTTP payload includes source",
    any("source" in p["json"] for p in weightings_http),
)

total = 6
if failures > 0:
    print(f"\033[91m{failures} failures\033[0m in {total} tests.")
    sys.exit(1)
else:
    print(f"All {total} all-tracks tests passed.")
