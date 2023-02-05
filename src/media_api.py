import json, sys, os, requests, datetime
from logic import getWeighting

if not os.environ.get("MEDIA_API"):
	sys.exit("\033[91mMEDIA_API not set\033[0m")
apiurl = os.environ.get("MEDIA_API")
if (apiurl.endswith("/")):
	sys.exit("\033[91mDon't include a trailing slash in the API url\033[0m")

def getAllTracks(page):
	return requests.get(apiurl+"/tracks/?page="+str(page)).json()

def updateWeighting(track):
	verbose = False
	if ('weighting' in track):
		oldweighting = track['weighting']
	else:
		oldweighting = "Not set"
	weighting = getWeighting(track, datetime.datetime.utcnow())
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
	timestampresult = requests.put(apiurl+"/globals/latest_weightings-timestamp", data=datetime.datetime.utcnow().isoformat().encode('utf-8'), allow_redirects=False)
	if timestampresult.ok:
		print ("\033[92mLast weightings timestamp updated: " +  timestampresult.text + "\033[0m")
	else:
		print ("\033[91m** Error ** HTTP Status code "+str(timestampresult.status_code)+" returned by API: " +  timestampresult.text + "\033[0m")
