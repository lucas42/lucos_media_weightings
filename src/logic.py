import datetime
import math
from log_util import error

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

def _parse_rfc3339(value):
	"""Parse an RFC 3339/ISO 8601 timestamp string into a timezone-aware datetime.
	Normalises Z-suffix to +00:00 (fromisoformat doesn't accept Z in Python < 3.11).
	If no timezone info is present, assumes UTC."""
	if value.endswith("Z"):
		value = value[:-1] + "+00:00"
	dt = datetime.datetime.fromisoformat(value)
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=datetime.timezone.utc)
	return dt

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

	is_new_track = False
	if 'added' in track['tags']:
		raw_tag = getTagValue(track['tags'], 'added')
		try:
			dateTimeAdded = _parse_rfc3339(raw_tag)
			delta = currentDateTime - dateTimeAdded
			if delta.days < 1:
				multiplier *= 100
				is_new_track = True
			elif delta.days < 14:
				multiplier *= 10
				is_new_track = True
		except Exception as e:
			error(f"Invalid added tag for track {getTrackId(track)}: {raw_tag!r} ({e})")

	# Apply current event multipliers based on about/mentions tags.
	# Also compute is_current_item for use in the recency penalty block below.
	is_current_item = False
	if currentItems:
		about_uris = getTagUris(track['tags'], 'about')
		mentions_uris = getTagUris(track['tags'], 'mentions')
		current_uris = {item['uri'] for item in currentItems}
		if about_uris & current_uris or mentions_uris & current_uris:
			is_current_item = True
		for uri in current_uris:
			if uri in about_uris:
				multiplier *= 100
			elif uri in mentions_uris:
				multiplier *= 20

	# Recency penalty: reduce multiplier if track was recently played.
	# Bypass if the track is about or mentions a current event (still relevant),
	# or if the track itself is new (added within the last 14 days).
	if 'lastSuccessfulPlay' in track['tags']:
		raw_tag = getTagValue(track['tags'], 'lastSuccessfulPlay')
		try:
			lastPlayed = _parse_rfc3339(raw_tag)
			if not is_current_item and not is_new_track:
				delta = currentDateTime - lastPlayed
				if delta.days < 1:
					multiplier /= 50
				elif delta.days < 7:
					multiplier /= 10
		except Exception as e:
			error(f"Invalid lastSuccessfulPlay tag for track {getTrackId(track)}: {raw_tag!r} ({e})")

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
