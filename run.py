#! /usr/local/bin/python3
import requests, json, sys
from func import getWeighting
if len(sys.argv) < 2:
	exit("Please specify API url")
apiurl = sys.argv[1]
page = 0
while True:
	page += 1
	tracks = requests.get(apiurl+"/tracks/?page="+str(page)).json()
	if len(tracks) == 0:
		break

	for track in tracks:
		weighting = getWeighting(track, isXmas = True)
		oldweighting = track['weighting']
		if (oldweighting != weighting):
			print(track['url'] + " " + str(oldweighting) + " => "+ str(weighting))
			print(json.dumps(track, indent=2))
			requests.put(apiurl+"/tracks/"+str(track['trackid'])+"/weighting", data=str(weighting))
		else:
			print(track['url'] + " - still " + str(weighting))