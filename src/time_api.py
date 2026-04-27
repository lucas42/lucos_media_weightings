import os, sys, requests
from log_util import info, error

if not os.environ.get("TIME_API"):
	error("TIME_API not set")
	sys.exit(1)
time_api_url = os.environ.get("TIME_API")
if time_api_url.endswith("/"):
	error("Don't include a trailing slash in the TIME_API url")
	sys.exit(1)

def getCurrentItems(timeout=30):
	"""Fetch current temporal items from lucos_time.

	Raises on failure (network error, non-2xx, malformed JSON) — callers
	should handle the exception. Previously this function swallowed errors
	and returned [], which silently degraded weighting calculation during
	time-API outages.
	"""
	response = requests.get(
		time_api_url + "/current-items",
		headers={'User-Agent': "lucos_media_weightings"},
		timeout=timeout,
	)
	response.raise_for_status()
	data = response.json()
	return data.get('items', [])
