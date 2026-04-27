import json, sys, os, requests
from datetime import datetime, timezone
from urllib.parse import urljoin
from logic import getWeighting, getTrackId
from time_api import getCurrentItems
from log_util import info, error, debug

if not os.environ.get("MEDIA_API"):
	error("MEDIA_API not set")
	sys.exit(1)
apiurl = os.environ.get("MEDIA_API")
if (apiurl.endswith("/")):
	error("Don't include a trailing slash in the API url")
	sys.exit(1)

if not os.environ.get("KEY_LUCOS_MEDIA_METADATA_API"):
	error("KEY_LUCOS_MEDIA_METADATA_API not set")
	sys.exit(1)
apiKey = os.environ.get("KEY_LUCOS_MEDIA_METADATA_API")

# Optional: the metadata manager's public base URL. When set, fetchTrack also
# accepts URLs from this origin and follows redirects to the API.
managerurl = os.environ.get("MEDIA_METADATA_MANAGER_ORIGIN", "").rstrip("/")

class getAllTracks:
	"""Returns an iterator covering all tracks in the media API

	Gets tracks one page at a time and returns them track-by-track
	When out of tracks, fetches the next page and returns those track-by-track
	Finishes when out of pages
	"""
	def __init__(self):
		self.page = 0
		self.tracks = []

	def __iter__(self):
		return self

	def __next__(self):

		# While there's still tracks left in the page of tracks, use the next of those
		if len(self.tracks) > 0:
			return self.tracks.pop(0)

		# If there's none left, fetch the next page
		self.page += 1
		response = requests.get(apiurl+"/v3/tracks?page="+str(self.page), headers={"Authorization":"Bearer "+apiKey}, timeout=30)
		response.raise_for_status()
		self.tracks = response.json()['tracks']

		if len(self.tracks) > 0:
			return self.tracks.pop(0)

		# If there's no tracks in the next page, then all tracks have been returned
		else:
			raise StopIteration

def fetchTrack(url, timeout=30):
	"""Fetch current track data from the given URL.

	Treats the webhook event URL as a notification — fetches the current
	state from the source system rather than trusting the event payload.
	This makes webhook retries safe from an ordering perspective.

	Accepts URLs from the configured media API (MEDIA_API) and, optionally,
	from the metadata manager (MEDIA_METADATA_MANAGER_ORIGIN). The manager redirects to the
	API; the redirect is followed manually so the Authorization header is
	re-sent on the cross-domain hop. An Accept: application/json header is
	included so the manager's content-negotiation returns the JSON redirect.

	Raises ValueError for URLs not matching a trusted origin.
	"""
	trusted_origins = [apiurl + "/"]
	if managerurl:
		trusted_origins.append(managerurl + "/")

	if not any(url.startswith(origin) for origin in trusted_origins):
		raise ValueError(f"URL must start with a trusted origin ({', '.join(trusted_origins)})")

	headers = {
		"Authorization": "Bearer " + apiKey,
		"Accept": "application/json",
	}

	# Use allow_redirects=False so we can re-send the Authorization header
	# after a cross-domain redirect (requests strips it by default).
	response = requests.get(url, headers=headers, allow_redirects=False, timeout=timeout)

	if response.is_redirect or response.is_permanent_redirect:
		redirect_url = urljoin(response.url, response.headers["Location"])
		# Validate the redirect destination is the trusted API
		if not redirect_url.startswith(apiurl + "/"):
			raise ValueError(f"Redirect target must be the configured media API ({apiurl}/)")
		response = requests.get(redirect_url, headers=headers, allow_redirects=True, timeout=timeout)

	response.raise_for_status()
	return response.json()

def updateWeighting(track, currentItems=None):
	if ('weighting' in track):
		oldweighting = track['weighting']
	else:
		oldweighting = "Not set"
	if currentItems is None:
		# getCurrentItems can raise if the time API is unreachable. We don't
		# want a transient time-API blip to fail an entire webhook call —
		# the only consequence of an empty currentItems is that the
		# current-event multipliers won't apply for this track. Log a
		# warning and continue.
		try:
			currentItems = getCurrentItems()
		except Exception as err:
			error(f"Time API call failed; falling back to empty currentItems: {err}")
			currentItems = []
	weighting = getWeighting(track, datetime.now(timezone.utc), currentItems=currentItems)
	if (oldweighting != weighting):
		debug(json.dumps(track, indent=2))
		result = requests.put(apiurl+"/v3/tracks/"+str(getTrackId(track))+"/weighting", data=str(weighting), allow_redirects=False, headers={"Authorization":"Bearer "+apiKey}, timeout=30)
		if result.is_redirect:
			raise Exception("Redirect returned by server.  Make sure you're using the latest API URL.")
		elif result.ok:
			return "Weighting changed to " + result.text
		else:
			raise Exception("HTTP Status code "+str(result.status_code)+" returned by API: " +  result.text)
	else:
		return "Weighting stayed the same"
