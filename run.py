#! /usr/local/bin/python3
import requests, json, sys, datetime
from func import getWeighting
verbose = False
if len(sys.argv) < 2:
	exit("Please specify API url")
apiurl = sys.argv[1]
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