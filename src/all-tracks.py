#! /usr/local/bin/python3
from media_api import getAllTracks, updateWeighting, updateWeightingsTimestamp
from loganne import loganneRequest

loganneRequest({
	"type":"weightings",
	"humanReadable": "Calculate weightings for all media tracks",
})
print ("\033[0mChecking media library for weightings which have changed...")

page = 0
while True:
	page += 1
	tracks = getAllTracks(page)
	if len(tracks) == 0:
		break

	for track in tracks:
		try:
			response = updateWeighting(track)
			print("\033[92m" + track['url'] + " - "+  response + "\033[0m")
		except Exception as error:
			print ("\033[91m** Error ** " + str(error) + "\033[0m")

updateWeightingsTimestamp()