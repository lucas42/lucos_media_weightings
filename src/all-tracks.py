#! /usr/local/bin/python3
from media_api import getAllTracks, updateWeighting
from time_api import getCurrentItems
from loganne import updateLoganne
from schedule_tracker import updateScheduleTracker
from log_util import info, error

# Record in loganne that the script has started
updateLoganne(
	type="weightings",
	humanReadable="Calculate weightings for all media tracks"
)
info("Checking media library for weightings which have changed...")

# Fetch current temporal items once for the entire run
currentItems = getCurrentItems()
info(f"Fetched {len(currentItems)} current items from lucos_time")

# Iterate through every track in the media API and try updating its weighting.
# Per-track errors are caught individually; a pagination-level failure (e.g. API
# timeout mid-way through pages) is caught at the outer level and reported as
# failure to the schedule tracker.
pagination_error = False
try:
	for track in getAllTracks():
		try:
			response = updateWeighting(track, currentItems=currentItems)
			if response != "Weighting stayed the same":
				info(track['url'] + " - "+  response)
		except Exception as err:
			error("** Error ** " + str(err))
except Exception as err:
	error(f"Pagination error: {str(err)}")
	pagination_error = True

updateScheduleTracker(success=not pagination_error)
