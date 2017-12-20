#! /usr/local/bin/python3

# Unit under test
from func import getWeighting

testcases = [
	{
		'comment': "Weightings default to 5",
		'payload': {
			'url': "http://example.com/audio.mp3",
			'tags': {
				'title': 'Joelyn',
				'artist': 'Dolly Parton',
			}
		},
		'expected': 5,
	},
	{
		'comment': "Weightings follow Ratings",
		'payload': {
			'url': "http://example.com/sumbarine.mp3",
			'tags': {
				'title': 'Yellow Submarine',
				'artist': 'The Beatles',
				'rating': "7.1",
			}
		},
		'expected': 7.1,
	},
	{
		'comment': "Speech tracks are rated lower",
		'payload': {
			'tags': {
				'title': 'Orson Welles, H.G.Wells - War Of The Worlds (The Original Broadcast Oct 30, 193', 
				'format': 'speech',
				'artist': 'Orson Welles',
			}
		},
		'expected': 0.5,
	},
	{
		'comment': "Christmas music is rare when not Christmas",
		'payload': {
			'url': "http://example.com/xmas.mp3",
			'tags': {
				'title': 'Christmas Time',
				'artist': 'The Darkness',
				'rating': "8.2",
				'event': 'xmas'
			}
		},
		'isXmas': False,
		'expected': 0.082,
	},
	{
		'comment': "Christmas music is more likely during Christmas",
		'payload': {
			'url': "http://example.com/xmas.mp3",
			'tags': {
				'title': 'Christmas Time',
				'artist': 'The Darkness',
				'rating': "8.2",
				'event': 'xmas',
			}
		},
		'isXmas': True,
		'expected': 82,
	},
	{
		'comment': "Hallowe'en music is more likely during Hallowe'en",
		'payload': {
			'url': "http://example.com/scary.mp3",
			'tags': {
				'title': 'Monster Mash',
				'rating': "6.5",
				'event': "Hallowe'en",
			}
		},
		'isHalloween': True,
		'expected': 325,
	},
	{
		'comment': "Eurovision music is more likely during the Eurovision Song Contest",
		'payload': {
			'url': "http://example.com/cheese.mp3",
			'tags': {
				'title': 'Wolves of the sea of the Sea',
				'rating': "9.2",
				'event': 'eurovision',
			}
		},
		'isEurovision': True,
		'expected': 920,
	},
]
failures = 0
for case in testcases:

	for key in ["isXmas", "isHalloween", "isEurovision"]:
		if key not in case:
			case[key] = False

	actual = getWeighting(case['payload'], isXmas = case['isXmas'], isEurovision = case['isEurovision'], isHalloween = case['isHalloween'])
	if (round(actual, 5) != round(case['expected'], 5)): # round to avoid irrelevant floating point nonsense
		print("Failed \"" + case['comment'] + "\".  Returned " + str(actual) + ", expected " + str(case['expected']))
		failures += 1

if (failures > 0):
	print(str(failures) + " failures in " + str(len(testcases)) + " cases.")
	exit(1)
else:
	print("All " + str(len(testcases)) + " cases passed.")