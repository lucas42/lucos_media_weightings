#! /usr/local/bin/python3
from media_api import getAllTracks, updateWeighting
from loganne import updateLoganne
from schedule_tracker import updateScheduleTracker
from log_util import info, error

# Record in loganne that the script has started
updateLoganne(
	type="weightings",
	humanReadable="Calculate weightings for all media tracks"
)
info("Checking media library for weightings which have changed...")

# Iterate through every track in the media API and try updating its weighting
for track in getAllTracks():
	try:
		response = updateWeighting(track)
		if response != "Weighting stayed the same":
			info(track['url'] + " - "+  response)
	except Exception as err:
		error("** Error ** " + str(err))

updateScheduleTracker(success=True)