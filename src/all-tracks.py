#! /usr/local/bin/python3
from media_api import getAllTracks, updateWeighting
from time_api import getCurrentItems
from loganne import updateLoganne
from schedule_tracker import updateScheduleTracker
from log_util import info, error

# Record in loganne that the script has started
updateLoganne(
	type="weightings",
	humanReadable="Calculating weightings for all media tracks"
)
info("Checking media library for weightings which have changed...")

# Fetch current temporal items once for the entire run.
# getCurrentItems can raise if the time API is unreachable. Don't fail
# the whole run for that — degrade gracefully to an empty list (the
# only consequence is that no current-event multipliers apply) and
# carry on. The /_info time-api-reachable check is the right place to
# surface a sustained outage.
try:
	currentItems = getCurrentItems()
	info(f"Fetched {len(currentItems)} current items from lucos_time")
except Exception as err:
	error(f"Time API call failed; falling back to empty currentItems: {err}")
	currentItems = []

# Iterate through every track in the media API and try updating its weighting.
# Per-track errors are caught individually; a pagination-level failure (e.g. API
# timeout mid-way through pages) is caught at the outer level and reported as
# failure to the schedule tracker.
pagination_error = None
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
	pagination_error = str(err)

if pagination_error is not None:
	updateScheduleTracker(success=False, message=pagination_error, job_name="all-tracks")
else:
	updateScheduleTracker(success=True, job_name="all-tracks")
