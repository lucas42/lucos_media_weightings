#! /usr/local/bin/python3
from media_api import getAllTracks, updateWeighting, updateWeightingsTimestamp
from loganne import loganneRequest
from schedule_tracker import updateScheduleTracker

# Record in loganne that the script has started
loganneRequest({
	"type":"weightings",
	"humanReadable": "Calculate weightings for all media tracks",
})
print ("\033[0mChecking media library for weightings which have changed...")

# Iterate through every track in the media API and try updating its weighting
for track in getAllTracks():
	try:
		response = updateWeighting(track)
		print("\033[92m" + track['url'] + " - "+  response + "\033[0m")
	except Exception as error:
		print ("\033[91m** Error ** " + str(error) + "\033[0m")

# Record the timestamp the script completed for monitoring and debug purposes
updateWeightingsTimestamp()
updateScheduleTracker()