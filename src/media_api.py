import json, sys, os, requests
from datetime import datetime
from logic import getWeighting
from time_api import getCurrentItems
from log_util import info, error

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

def normalizeV3Tags(tags):
	"""Convert V3 structured tags to flat strings for backwards compatibility.

	V3 tags are dicts of predicate to arrays of {"name": ..., "uri": ...} objects.
	This converts them to simple strings (single-value) or comma-separated strings
	(multi-value), matching the format logic.py expects.
	"""
	result = {}
	for key, values in tags.items():
		if not isinstance(values, list):
			result[key] = values
			continue
		names = [v.get("name", "") for v in values if v.get("name", "")]
		if not names:
			result[key] = None
		elif len(names) == 1:
			result[key] = names[0]
		else:
			result[key] = ",".join(names)
	return result

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
		tracks = requests.get(apiurl+"/v3/tracks?page="+str(self.page), headers={"Authorization":"Bearer "+apiKey}).json()['tracks']
		self.tracks = [normalizeTrack(t) for t in tracks]

		if len(self.tracks) > 0:
			return self.tracks.pop(0)

		# If there's no tracks in the next page, then all tracks have been returned
		else:
			raise StopIteration

def normalizeTrack(track):
	"""Normalize a V3 track response for use with logic.py.

	Converts V3 structured tags to flat strings and maps 'id' field.
	"""
	if "tags" in track:
		track["tags"] = normalizeV3Tags(track["tags"])
	return track

def updateWeighting(track, currentItems=None):
	verbose = False
	if ('weighting' in track):
		oldweighting = track['weighting']
	else:
		oldweighting = "Not set"
	if currentItems is None:
		currentItems = getCurrentItems()
	weighting = getWeighting(track, datetime.utcnow(), currentItems=currentItems)
	if (oldweighting != weighting):
		if verbose:
			print(json.dumps(track, indent=2))
		result = requests.put(apiurl+"/v3/tracks/"+str(track['id'])+"/weighting", data=str(weighting), allow_redirects=False, headers={"Authorization":"Bearer "+apiKey})
		if result.is_redirect:
			raise Exception("Redirect returned by server.  Make sure you're using the latest API URL.")
		elif result.ok:
			return "Weighting changed to " + result.text
		else:
			raise Exception("HTTP Status code "+str(result.status_code)+" returned by API: " +  result.text)
	else:
		return "Weighting stayed the same"
