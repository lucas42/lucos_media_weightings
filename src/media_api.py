import json, sys, os, requests
from datetime import datetime
from logic import getWeighting

if not os.environ.get("MEDIA_API"):
	sys.exit("\033[91mMEDIA_API not set\033[0m")
apiurl = os.environ.get("MEDIA_API")
if (apiurl.endswith("/")):
	sys.exit("\033[91mDon't include a trailing slash in the API url\033[0m")


if not os.environ.get("KEY_LUCOS_MEDIA_METADATA_API"):
	sys.exit("\033[91mKEY_LUCOS_MEDIA_METADATA_API not set\033[0m")
apiKey = os.environ.get("KEY_LUCOS_MEDIA_METADATA_API")

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
		self.tracks = requests.get(apiurl+"/v2/tracks/?page="+str(self.page), headers={"Authorization":"key "+apiKey}).json()['tracks']

		if len(self.tracks) > 0:
			return self.tracks.pop(0)

		# If there's no tracks in the next page, then all tracks have been returned
		else:
			raise StopIteration

def updateWeighting(track):
	verbose = False
	if ('weighting' in track):
		oldweighting = track['weighting']
	else:
		oldweighting = "Not set"
	weighting = getWeighting(track, datetime.utcnow())
	if (oldweighting != weighting):
		if verbose:
			print(json.dumps(track, indent=2))
		result = requests.put(apiurl+"/v2/tracks/"+str(track['trackid'])+"/weighting", data=str(weighting), allow_redirects=False, headers={"Authorization":"key "+apiKey})
		if result.is_redirect:
			raise Exception("Redirect returned by server.  Make sure you're using the latest API URL.")
		elif result.ok:
			return "Weighting changed to " + result.text
		else:
			raise Exception("HTTP Status code "+str(result.status_code)+" returned by API: " +  result.text)
	else:
		return "Weighting stayed the same"
