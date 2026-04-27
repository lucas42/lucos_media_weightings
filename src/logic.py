import datetime
import math

def soft_cap(raw_multiplier, cap=100):
	return cap * (1 - math.exp(-raw_multiplier / cap))

def getTagValue(tags, key, default=None):
	"""Get the value of a tag from a v3 array-of-objects format: [{name, uri}, ...]."""
	if key not in tags or not tags[key]:
		return default
	val = tags[key]
	return val[0].get('name', default)

def getTrackId(track):
	"""Get the track ID from a v3 track payload ('id' field)."""
	return track.get('id')

def getTagUris(tags, key):
	"""Get the set of URIs from a v3 tag array: [{name, uri}, ...]."""
	if key not in tags:
		return set()
	val = tags[key]
	return {v['uri'] for v in val if v.get('uri')}

def getWeighting(track, currentDateTime, isEurovision = False, currentItems = None):
	collection_slugs = list(map(lambda collection: collection['slug'], track['collections']))

	weighting = 5
	if 'rating' in track['tags']:
		rating = float(getTagValue(track['tags'], 'rating', '0'))
		if rating < 2:
			weighting = 0
		else:
			weighting = rating

	multiplier = 1

	isXmas = (currentDateTime.month == 12)
	if 'christmas' in collection_slugs:
		if isXmas:
			multiplier *= 10
		else:
			weighting /= 100

	isHalloween = (currentDateTime.month == 10 and currentDateTime.day > 25)
	if 'halloween' in collection_slugs:
		if isHalloween:
			multiplier *= 50

	if 'eurovision' in collection_slugs:
		if isEurovision:
			multiplier *= 100

	if 'added' in track['tags']:
		try:
			addedTag = getTagValue(track['tags'], 'added')

			# Normalise to UTC-aware datetime.
			# Handle Z-suffix (Zulu/UTC) and naive timestamps (assumed UTC) consistently.
			if addedTag.endswith("Z"):
				addedTag = addedTag[:-1] + "+00:00"
			else:
				addedTag = addedTag + "+00:00"
			dateTimeAdded = datetime.datetime.fromisoformat(addedTag)
			delta = currentDateTime - dateTimeAdded
			if delta.days < 1:
				multiplier *= 100
			elif delta.days < 14:
				multiplier *= 10

		# Ignore invalid dates in 'added' tag
		except Exception:
			pass

	# Apply current event multipliers based on about/mentions tags
	if currentItems:
		about_uris = getTagUris(track['tags'], 'about')
		mentions_uris = getTagUris(track['tags'], 'mentions')
		current_uris = {item['uri'] for item in currentItems}

		for uri in current_uris:
			if uri in about_uris:
				multiplier *= 100
			elif uri in mentions_uris:
				multiplier *= 20

	weighting *= soft_cap(multiplier, cap=100)

	if 'speech' in collection_slugs:
		weighting = 0
	if 'fx' in collection_slugs:
		weighting = 0
	if 'podcasts' in collection_slugs:
		weighting = 0

	if 'duration' in track:
		if track['duration'] > 1800:
			weighting = 0

	if 'karaoke' in collection_slugs:
		weighting = 0

	return weighting
