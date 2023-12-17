#! /usr/local/bin/python3
import datetime

# Unit under test
from src.logic import getWeighting

testcases = [
	{
		'comment': "Weightings default to 5",
		'payload': {
			'url': "http://example.com/audio.mp3",
			'tags': {
				'title': 'Joelyn',
				'artist': 'Dolly Parton',
			},
			'duration': 500,
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
	{
		'comment': "New music added in the past 2 weeks is more likely",
		'payload': {
			'url': "http://example.com/new.mp3",
			'tags': {
				'title': 'New Music just dropped',
				'rating': "7",
				'added': "2030-02-01T23:00",
			}
		},
		'datetime': "2030-02-10T12:30",
		'expected': 70,
	},
	{
		'comment': "Brand new music added in the past 24 hours is very likely",
		'payload': {
			'url': "http://example.com/brand-new.mp3",
			'tags': {
				'title': 'Brand New Music just dropped',
				'rating': "8",
				'added': "2020-03-04T21:21",
			}
		},
		'datetime': "2020-03-05T12:30",
		'expected': 800,
	},
	{
		'comment': "Music added more than a fortnight ago is same as default",
		'payload': {
			'url': "http://example.com/not-new.mp3",
			'tags': {
				'title': 'Older Music',
				'rating': "8.4",
				'added': "2025-08-08T21:21",
			}
		},
		'datetime': "2025-09-05T12:30",
		'expected': 8.4,
	},
	{
		'comment': "Invalid added tag is ignored",
		'payload': {
			'url': "http://example.com/song.mp3",
			'tags': {
				'title': 'Music of Unknown Age',
				'rating': "7.7",
				'added': "1209238492842098",
			}
		},
		'datetime': "1990-09-05T12:30",
		'expected': 7.7,
	},
	{
		'comment': "Added tags with a trailing Z are parsed as expected",
		'payload': {
			'url': "http://example.com/new.mp3",
			'tags': {
				'title': 'More New Music just dropped',
				'rating': "8",
				'added': "2030-02-01T23:00Z",
			}
		},
		'datetime': "2030-02-10T12:30",
		'expected': 80,
	},
	{
		'comment': "Really long tracks (eg full albums) are zero weighted",
		'payload': {
			'url': "http://example.com/full-album.mp3",
			'tags': {
				'title': 'The Best of Some Band - Full Album',
			},
			'duration': 1912,
		},
		'expected': 0,
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
		print("\033[91mFailed\033[0m \"" + case['comment'] + "\".  Returned \033[91m" + str(actual) + "\033[0m, expected " + str(case['expected']))
		failures += 1

if (failures > 0):
	print("\033[91m"+str(failures) + " failures\033[0m in " + str(len(testcases)) + " cases.")
	exit(1)
else:
	print("All " + str(len(testcases)) + " cases passed.")