
def getWeighting(track, isXmas = False, isHalloween = False, isEurovision = False):
	weighting = 5
	if 'rating' in track['tags']:
		weighting = float(track['tags']['rating'])

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

	if 'format' in track['tags']:
		if track['tags']['format'] == "speech":
			weighting = 0.5
		if track['tags']['format'] == "fx":
			weighting = 0.5
		if track['tags']['format'] == "podcast":
			weighting = 0.5

	return weighting