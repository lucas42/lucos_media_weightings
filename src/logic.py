import datetime

def getWeighting(track, currentDateTime, isEurovision = False):
	collection_slugs = list(map(lambda collection: collection['slug'], track['collections']))

	weighting = 5
	if 'rating' in track['tags']:
		rating = float(track['tags']['rating'])
		if rating < 2:
			weighting = 0
		else:
			weighting = rating

	isXmas = (currentDateTime.month == 12)
	if 'christmas' in collection_slugs:
		if isXmas:
			weighting *= 10
		else:
			weighting /= 100

	isHalloween = (currentDateTime.month == 10 and currentDateTime.day > 25)
	if 'halloween' in collection_slugs:
		if isHalloween:
			weighting *= 50

	if 'eurovision' in collection_slugs:
		if isEurovision:
			weighting *= 100

	if 'added' in track['tags']:
		try:
			addedTag = track['tags']['added']

			# RFC3339 and ISO 8601 are similar, but not exactly the same
			# But if one ends in a Z (for Zulu-time), we can strip that off the end and treat it as if it's not there
			if addedTag[-1] == "Z":
				addedTag = addedTag[:-1]
			dateTimeAdded = datetime.datetime.fromisoformat(addedTag)
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

	if 'duration' in track:
		if track['duration'] > 1800:
			weighting = 0

	return weighting