import json, sys, os, requests
from datetime import datetime
from logic import getWeighting

if not os.environ.get("MEDIA_API"):
	sys.exit("\033[91mMEDIA_API not set\033[0m")
apiurl = os.environ.get("MEDIA_API")
if (apiurl.endswith("/")):
	sys.exit("\033[91mDon't include a trailing slash in the API url\033[0m")

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
		self.tracks = requests.get(apiurl+"/tracks/?page="+str(self.page)).json()

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
		result = requests.put(apiurl+"/tracks/"+str(track['trackid'])+"/weighting", data=str(weighting), allow_redirects=False)
		if result.is_redirect:
			raise Exception("Redirect returned by server.  Make sure you're using the latest API URL.")
		elif result.ok:
			return "Weighting changed to " + result.text
		else:
			raise Exception("HTTP Status code "+str(result.status_code)+" returned by API: " +  result.text)
	else:
		return "Weighting stayed the same"


# Save the current time as a global in the media API
def updateWeightingsTimestamp():
	timestampresult = requests.put(apiurl+"/globals/latest_weightings-timestamp", data=datetime.utcnow().isoformat().encode('utf-8'), allow_redirects=False)
	if timestampresult.ok:
		print ("\033[92mLast weightings timestamp updated: " +  timestampresult.text + "\033[0m")
	else:
		print ("\033[91m** Error ** HTTP Status code "+str(timestampresult.status_code)+" returned by API: " +  timestampresult.text + "\033[0m")

def getWeightingsTimestampAge():
	""" Returns the number of seconds since the all-tracks script last successfully completed """
	response = requests.get(apiurl+"/globals/latest_weightings-timestamp")
	if not response.ok:
		raise Exception("HTTP Status code "+str(result.status_code)+" returned by API: " +  result.text)
	last_script_time = datetime.fromisoformat(str(response.text))
	since_script = datetime.now() - last_script_time
	return since_script.total_seconds()
