"""Reachability probes for upstream services.

Used by /_info to surface whether MEDIA_API and TIME_API are responsive,
so silent webhook-handling failures aren't masked by the lack of a
proactive check.

The probe budget is tight: lucos_monitoring fetches /_info with a 1s
hard timeout. We probe both upstreams concurrently so the worst-case
contribution to /_info is ~one timeout, not the sum.
"""
import os
import requests
from concurrent.futures import ThreadPoolExecutor

UPSTREAM_TIMEOUT_SECONDS = 0.5


def _probe(url):
	"""Probe a single upstream /_info. Returns (ok: bool, debug: str|None)."""
	if not url:
		return False, "URL not configured"
	try:
		r = requests.get(
			url.rstrip("/") + "/_info",
			timeout=UPSTREAM_TIMEOUT_SECONDS,
			headers={"User-Agent": "lucos_media_weightings/health-check"},
		)
		if r.status_code != 200:
			return False, f"HTTP {r.status_code}"
		return True, None
	except requests.exceptions.Timeout:
		return False, f"Timeout after {UPSTREAM_TIMEOUT_SECONDS}s"
	except requests.exceptions.RequestException as e:
		return False, f"{type(e).__name__}: {e}"


def probe_upstreams():
	"""Concurrently probe MEDIA_API and TIME_API. Returns dict of check entries."""
	media_api = os.environ.get("MEDIA_API", "")
	time_api = os.environ.get("TIME_API", "")

	with ThreadPoolExecutor(max_workers=2) as pool:
		media_future = pool.submit(_probe, media_api)
		time_future = pool.submit(_probe, time_api)
		media_ok, media_debug = media_future.result()
		time_ok, time_debug = time_future.result()

	checks = {
		"media-api-reachable": {
			"techDetail": f"GETs {media_api}/_info with a {UPSTREAM_TIMEOUT_SECONDS}s timeout to confirm the media metadata API is responsive — every webhook handler call depends on this",
			"ok": media_ok,
		},
		"time-api-reachable": {
			"techDetail": f"GETs {time_api}/_info with a {UPSTREAM_TIMEOUT_SECONDS}s timeout to confirm lucos_time is responsive — current-events weighting depends on this",
			"ok": time_ok,
		},
	}
	if media_debug:
		checks["media-api-reachable"]["debug"] = media_debug
	if time_debug:
		checks["time-api-reachable"]["debug"] = time_debug
	return checks
