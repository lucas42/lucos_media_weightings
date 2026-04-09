#! /usr/bin/env python3
"""Unit tests for is_authorised() and _get_valid_keys() in server.py.

Run from src/ directory: python3 test_auth.py
"""
import os
import sys

# Set required env vars before importing server.py to avoid module-level exits
os.environ.setdefault("PORT", "8080")
os.environ.setdefault("TIME_API", "http://stub")

# Minimal stubs so server.py can be imported without its runtime dependencies
import types

# Stub out all non-stdlib modules server.py imports
for mod_name in ("media_api", "schedule_tracker", "time_api", "loganne"):
	stub = types.ModuleType(mod_name)
	stub.updateWeighting = None  # satisfy 'from media_api import updateWeighting'
	sys.modules[mod_name] = stub

from server import _get_valid_keys, is_authorised

failures = 0

def run(comment, environ, client_keys, expected):
	global failures
	if client_keys is not None:
		os.environ["CLIENT_KEYS"] = client_keys
	elif "CLIENT_KEYS" in os.environ:
		del os.environ["CLIENT_KEYS"]
	actual = is_authorised(environ)
	if actual != expected:
		print(f"\033[91mFailed\033[0m {comment}. Returned \033[91m{actual}\033[0m, expected {expected}")
		failures += 1

def run_key_parse(comment, client_keys, expected):
	global failures
	if client_keys is not None:
		os.environ["CLIENT_KEYS"] = client_keys
	elif "CLIENT_KEYS" in os.environ:
		del os.environ["CLIENT_KEYS"]
	actual = _get_valid_keys()
	if actual != expected:
		print(f"\033[91mFailed\033[0m {comment}. Returned \033[91m{actual}\033[0m, expected {expected}")
		failures += 1

# _get_valid_keys tests
run_key_parse("_get_valid_keys returns empty set when CLIENT_KEYS not set", None, set())
run_key_parse("_get_valid_keys parses single pair", "svc=mytoken", {"mytoken"})
run_key_parse("_get_valid_keys parses multiple pairs", "a=tokenA;b=tokenB", {"tokenA", "tokenB"})

# is_authorised tests (Phase 1 behaviour)
is_authorised_tests = [
	("no CLIENT_KEYS → accept", {}, None, True),
	("valid token → accept", {"HTTP_AUTHORIZATION": "Bearer mysecrettoken"}, "svc=mysecrettoken", True),
	("missing header → accept during Phase 1 migration", {}, "svc=mysecrettoken", True),
	("invalid token → reject", {"HTTP_AUTHORIZATION": "Bearer wrongtoken"}, "svc=mysecrettoken", False),
	("no Bearer prefix → reject", {"HTTP_AUTHORIZATION": "mysecrettoken"}, "svc=mysecrettoken", False),
	("multiple keys, first matches", {"HTTP_AUTHORIZATION": "Bearer tokenA"}, "a=tokenA;b=tokenB", True),
	("multiple keys, second matches", {"HTTP_AUTHORIZATION": "Bearer tokenB"}, "a=tokenA;b=tokenB", True),
	("multiple keys, none match", {"HTTP_AUTHORIZATION": "Bearer tokenC"}, "a=tokenA;b=tokenB", False),
]

for comment, environ, client_keys, expected in is_authorised_tests:
	run(comment, environ, client_keys, expected)

if "CLIENT_KEYS" in os.environ:
	del os.environ["CLIENT_KEYS"]

total = 3 + len(is_authorised_tests)
if failures > 0:
	print(f"\033[91m{failures} failures\033[0m in {total} tests.")
	sys.exit(1)
else:
	print(f"All {total} auth tests passed.")
