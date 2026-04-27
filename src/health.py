"""Reachability probes for upstream services.

Used by /_info to surface whether MEDIA_API and TIME_API are responsive,
so silent webhook-handling failures aren't masked by the lack of a
proactive check.

These checks call the real production functions (fetchTrack, getCurrentItems)
rather than just probing /_info, so they exercise the same authentication and
data-access code paths used by the webhook handler. A passing health check
therefore implies the actual workload would succeed too.

The probe budget is tight: lucos_monitoring fetches /_info with a 1s hard
timeout. Each probe runs with a 0.5s timeout and the two are run concurrently,
so worst-case /_info latency is ~0.5s rather than ~1s.

Imports of media_api and time_api are deferred to call-time so that test
modules which stub those modules can import server.py (and transitively
health.py) without needing to add attributes to their stubs.
"""
from concurrent.futures import ThreadPoolExecutor

UPSTREAM_TIMEOUT_SECONDS = 0.5

# Number of consecutive poll failures lucos_monitoring should tolerate before
# alerting. Gives wiggle room for the occasional transient blip without
# masking a sustained outage. Same precedent as fetch-info / tls-certificate
# in lucos_monitoring's own checks.
FAIL_THRESHOLD = 2


def _media_api_healthcheck_url():
	"""Construct the media-API URL the health check hits.

	/v3/tracks/1 is the cheapest authenticated single-track endpoint —
	matches the precedent set by lucos_media_metadata_manager's /_info.
	Relies on track id 1 existing, which is a stable assumption in lucos.
	"""
	from media_api import apiurl
	return apiurl + "/v3/tracks/1"


def _probe_media_api():
	"""Returns (ok: bool, debug: str|None)."""
	from media_api import fetchTrack
	try:
		fetchTrack(_media_api_healthcheck_url(), timeout=UPSTREAM_TIMEOUT_SECONDS)
		return True, None
	except Exception as e:
		return False, f"{type(e).__name__}: {e}"


def _probe_time_api():
	"""Returns (ok: bool, debug: str|None)."""
	from time_api import getCurrentItems
	try:
		getCurrentItems(timeout=UPSTREAM_TIMEOUT_SECONDS)
		return True, None
	except Exception as e:
		return False, f"{type(e).__name__}: {e}"


def probe_upstreams():
	"""Concurrently probe MEDIA_API and TIME_API. Returns dict of check entries."""
	with ThreadPoolExecutor(max_workers=2) as pool:
		media_future = pool.submit(_probe_media_api)
		time_future = pool.submit(_probe_time_api)
		media_ok, media_debug = media_future.result()
		time_ok, time_debug = time_future.result()

	checks = {
		"media-api-reachable": {
			"techDetail": f"Calls fetchTrack() against {_media_api_healthcheck_url()} with a {UPSTREAM_TIMEOUT_SECONDS}s timeout — exercises the same authenticated GET path as the webhook handler",
			"ok": media_ok,
			"failThreshold": FAIL_THRESHOLD,
		},
		"time-api-reachable": {
			"techDetail": f"Calls getCurrentItems() with a {UPSTREAM_TIMEOUT_SECONDS}s timeout — exercises the same /current-items call as updateWeighting",
			"ok": time_ok,
			"failThreshold": FAIL_THRESHOLD,
		},
	}
	if media_debug:
		checks["media-api-reachable"]["debug"] = media_debug
	if time_debug:
		checks["time-api-reachable"]["debug"] = time_debug
	return checks
