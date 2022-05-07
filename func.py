import datetime

def getWeighting(track, currentDateTime, isEurovision = False):
	isXmas = (currentDateTime.month == 12)
	isHalloween = (currentDateTime.month == 10 and currentDateTime.day > 25)
	weighting = 5
	if 'rating' in track['tags']:
		rating = float(track['tags']['rating'])
		if rating < 2:
			weighting = 0
		else:
			weighting = rating

	if 'event' in track['tags']:
		event = track['tags']['event'].lower()
		if event == "xmas":
			if isXmas:
				weighting *= 10
			else:
				weighting /= 100
		elif event == "hallowe'en":
			if isHalloween:
				weighting *= 50
		elif event == "eurovision":
			if isEurovision:
				weighting *= 100

	if 'added' in track['tags']:
		try:
			dateTimeAdded = datetime.datetime.fromisoformat(track['tags']['added'])
			delta = currentDateTime - dateTimeAdded
			if delta.days < 1:
				weighting *= 100
			elif delta.days < 14:
				weighting *= 10

		# Ignore invalid dates in 'added' tag
		except Exception:
			pass

	if 'format' in track['tags']:
		if track['tags']['format'] == "speech":
			weighting = 0
		if track['tags']['format'] == "fx":
			weighting = 0
		if track['tags']['format'] == "podcast":
			weighting = 0

	return weighting