import json, requests, os, sys
from log_util import info, error

SCHEDULE_TRACKER_ENDPOINT = os.environ.get('SCHEDULE_TRACKER_ENDPOINT')
if not SCHEDULE_TRACKER_ENDPOINT:
	error("SCHEDULE_TRACKER_ENDPOINT environment variable not set - needs to be the URL of a running lucos_contacts instance.")
	sys.exit(1)

# Inform the schedule tracker that the job is complete
def updateScheduleTracker(success=True, message=None):
	payload = {
		"system": "lucos_media_weightings",
		"frequency": 24 * 60 * 60, # 1 day, in seconds
		"status": "success" if success else "error",
		"message": message,
	}
	schedule_tracker_response = requests.post(SCHEDULE_TRACKER_ENDPOINT, json=payload);
	if not schedule_tracker_response.ok:
		error("Call to schedule-tracker failed with "+str(schedule_tracker_response.status_code)+" response: " +  schedule_tracker_response.text)