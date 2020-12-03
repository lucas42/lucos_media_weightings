#! /usr/local/bin/python3
import requests, json, sys, datetime, os
from func import getWeighting
verbose = False
if not os.environ.get("MEDIA_API"):
	sys.exit("\033[91mMEDIA_API not set\033[0m")
apiurl = os.environ.get("MEDIA_API")
if (apiurl.endswith("/")):
	sys.exit("\033[91mDon't include a trailing slash in the API url\033[0m")
page = 0

today = datetime.date.today()
isDecember = (today.month == 12)
isLateOctober = (today.month == 10 and today.day > 25)

print ("\033[0mChecking media library for weightings which have changed...")
while True:
	page += 1
	tracks = requests.get(apiurl+"/tracks/?page="+str(page)).json()
	if len(tracks) == 0:
		break

	for track in tracks:
		weighting = getWeighting(track, isXmas = isDecember, isHalloween = isLateOctober)
		if ('weighting' in track):
			oldweighting = track['weighting']
		else:
			oldweighting = "Not set"
		if (oldweighting != weighting):
			print("\033[1mWeighting update: " + track['url'] + " " + str(oldweighting) + " => " + str(weighting)+ "\033[0m")
			if verbose:
				print(json.dumps(track, indent=2))
			result = requests.put(apiurl+"/tracks/"+str(track['trackid'])+"/weighting", data=str(weighting), allow_redirects=False)
			if result.is_redirect:
				print ("\033[91m** Error ** Redirect returned by server.  Make sure you're using the latest API URL. \033[0m")
			elif result.ok:
				print ("\033[92mWeighting updated to: " +  result.text + "\033[0m")
			else:
				print ("\033[91m** Error ** HTTP Status code "+str(result.status_code)+" returned by API: " +  result.text + "\033[0m")
		else:
			print(track['url'] + " - still " + str(weighting))

# Save the current time as a global in the media API
timestampresult = requests.put(apiurl+"/globals/latest_weightings-timestamp", data=datetime.datetime.utcnow().isoformat().encode('utf-8'), allow_redirects=False)
if timestampresult.ok:
	print ("\033[92mLast weightings timestamp updated: " +  timestampresult.text + "\033[0m")
else:
	print ("\033[91m** Error ** HTTP Status code "+str(timestampresult.status_code)+" returned by API: " +  timestampresult.text + "\033[0m")
