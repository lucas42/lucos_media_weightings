#! /usr/bin/env python3
"""Unit tests for all-tracks.py.

Verifies that the loganne event is emitted with level='detail', confirming
that the weighting-recalculation churn is kept out of the default loganne feed
(per loganne ADR-0001).

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

# Build stubs for every module all-tracks.py imports
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
_script_path = pathlib.Path(__file__).parent / "all-tracks.py"
spec = importlib.util.spec_from_file_location("all_tracks", _script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Clean up stubs so other test files can import the real modules
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

total = 3
if failures > 0:
    print(f"\033[91m{failures} failures\033[0m in {total} tests.")
    sys.exit(1)
else:
    print(f"All {total} all-tracks tests passed.")
