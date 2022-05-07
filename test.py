#! /usr/local/bin/python3
import datetime

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
		'comment': "Lowest ratings are rated zero",
		'payload': {
			'url': "http://example.com/random-south-park-track",
			'tags': {
				'title': 'Singing rude stuff in silly voices',
				'artist': 'South Park',
				'rating': "0.4",
			}
		},
		'expected': 0,
	},
	{
		'comment': "Speech tracks are rated zero",
		'payload': {
			'tags': {
				'title': 'Orson Welles, H.G.Wells - War Of The Worlds (The Original Broadcast Oct 30, 193', 
				'format': 'speech',
				'artist': 'Orson Welles',
			}
		},
		'expected': 0,
	},
	{
		'comment': "Sound effects are rated zero",
		'payload': {
			'url': "http://example.com/bang.mp3",
			'tags': {
				'title': 'Explosion', 
				'format': 'fx',
			}
		},
		'expected': 0,
	},
	{
		'comment': "Podcasts are rated zero",
		'payload': {
			'url': "http://example.com/podcast-episode3.mp3",
			'tags': {
				'title': 'Episode 3', 
				'format': 'podcast',
			}
		},
		'expected': 0,
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
		'datetime': "2050-09-29",
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
		'datetime': "2012-12-02",
		'expected': 82,
	},
	{
		'comment': "Hallowe'en music is more likely at end of October",
		'payload': {
			'url': "http://example.com/scary.mp3",
			'tags': {
				'title': 'Monster Mash',
				'rating': "6.5",
				'event': "Hallowe'en",
			}
		},
		'datetime': "1998-10-30",
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

	if "isEurovision" not in case:
		case["isEurovision"] = False
	if "datetime" not in case:
		case["datetime"] = "2000-01-01T17:00"
	currentDateTime = datetime.datetime.fromisoformat(case['datetime'])

	actual = getWeighting(case['payload'], currentDateTime, isEurovision = case['isEurovision'], )
	if (round(actual, 5) != round(case['expected'], 5)): # round to avoid irrelevant floating point nonsense
		print("Failed \"" + case['comment'] + "\".  Returned " + str(actual) + ", expected " + str(case['expected']))
		failures += 1

if (failures > 0):
	print(str(failures) + " failures in " + str(len(testcases)) + " cases.")
	exit(1)
else:
	print("All " + str(len(testcases)) + " cases passed.")