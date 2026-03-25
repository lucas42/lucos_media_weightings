#! /usr/local/bin/python3
import datetime

# Unit under test
from src.logic import getWeighting, soft_cap

testcases = [
	{
		'comment': "Weightings default to 5",
		'payload': {
			'url': "http://example.com/audio.mp3",
			'tags': {
				'title': 'Joelyn',
				'artist': 'Dolly Parton',
			},
			'collections': [],
			'duration': 500,
		},
		'expected': 4.97508,
	},
	{
		'comment': "Weightings follow Ratings",
		'payload': {
			'url': "http://example.com/sumbarine.mp3",
			'tags': {
				'title': 'Yellow Submarine',
				'artist': 'The Beatles',
				'rating': "7.1",
			},
			'collections': [],
		},
		'expected': 7.06462,
	},
	{
		'comment': "Lowest ratings are rated zero",
		'payload': {
			'url': "http://example.com/random-south-park-track",
			'tags': {
				'title': 'Singing rude stuff in silly voices',
				'artist': 'South Park',
				'rating': "0.4",
			},
			'collections': [],
		},
		'expected': 0,
	},
	{
		'comment': "Speech tracks are rated zero",
		'payload': {
			'tags': {
				'title': 'Orson Welles, H.G.Wells - War Of The Worlds (The Original Broadcast Oct 30, 193',
				'artist': 'Orson Welles',
			},
			'collections': [
				{
					'slug': 'speech',
				},
			],
		},
		'expected': 0,
	},
	{
		'comment': "Sound effects are rated zero",
		'payload': {
			'url': "http://example.com/bang.mp3",
			'tags': {
				'title': 'Explosion',
			},
			'collections': [
				{
					'slug': 'fx',
				},
			],
		},
		'expected': 0,
	},
	{
		'comment': "Podcasts are rated zero",
		'payload': {
			'url': "http://example.com/podcast-episode3.mp3",
			'tags': {
				'title': 'Episode 3',
			},
			'collections': [
				{
					'slug': 'podcasts',
				},
			],
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
			},
			'collections': [
				{
					'slug': 'christmas',
				},
			],
		},
		'datetime': "2050-09-29",
		'expected': 0.08159,
	},
	{
		'comment': "Christmas music is more likely during Christmas",
		'payload': {
			'url': "http://example.com/xmas.mp3",
			'tags': {
				'title': 'Christmas Time',
				'artist': 'The Darkness',
				'rating': "8.2",
			},
			'collections': [
				{
					'slug': 'christmas',
					'name': "Christmas",
				},
			],
		},
		'datetime': "2012-12-02",
		'expected': 78.03332,
	},
	{
		'comment': "Hallowe'en music is more likely at end of October",
		'payload': {
			'url': "http://example.com/scary.mp3",
			'tags': {
				'title': 'Monster Mash',
				'rating': "6.5",
			},
			'collections': [
				{
					'slug': 'halloween',
				},
			],
		},
		'datetime': "1998-10-30",
		'expected': 255.75507,
	},
	{
		'comment': "Eurovision music is more likely during the Eurovision Song Contest",
		'payload': {
			'url': "http://example.com/cheese.mp3",
			'tags': {
				'title': 'Wolves of the sea of the Sea',
				'rating': "9.2",
			},
			'collections': [
				{
					'slug': 'eurovision',
				},
			],
		},
		'isEurovision': True,
		'expected': 581.55091,
	},
	{
		'comment': "New music added in the past 2 weeks is more likely",
		'payload': {
			'url': "http://example.com/new.mp3",
			'tags': {
				'title': 'New Music just dropped',
				'rating': "7",
				'added': "2030-02-01T23:00",
			},
			'collections': [],
		},
		'datetime': "2030-02-10T12:30",
		'expected': 66.61381,
	},
	{
		'comment': "Brand new music added in the past 24 hours is very likely",
		'payload': {
			'url': "http://example.com/brand-new.mp3",
			'tags': {
				'title': 'Brand New Music just dropped',
				'rating': "8",
				'added': "2020-03-04T21:21",
			},
			'collections': [],
		},
		'datetime': "2020-03-05T12:30",
		'expected': 505.69645,
	},
	{
		'comment': "Music added more than a fortnight ago is same as default",
		'payload': {
			'url': "http://example.com/not-new.mp3",
			'tags': {
				'title': 'Older Music',
				'rating': "8.4",
				'added': "2025-08-08T21:21",
			},
			'collections': [],
		},
		'datetime': "2025-09-05T12:30",
		'expected': 8.35814,
	},
	{
		'comment': "Invalid added tag is ignored",
		'payload': {
			'url': "http://example.com/song.mp3",
			'tags': {
				'title': 'Music of Unknown Age',
				'rating': "7.7",
				'added': "1209238492842098",
			},
			'collections': [],
		},
		'datetime': "1990-09-05T12:30",
		'expected': 7.66163,
	},
	{
		'comment': "Added tags with a trailing Z are parsed as expected",
		'payload': {
			'url': "http://example.com/new.mp3",
			'tags': {
				'title': 'More New Music just dropped',
				'rating': "8",
				'added': "2030-02-01T23:00Z",
			},
			'collections': [],
		},
		'datetime': "2030-02-10T12:30",
		'expected': 76.13007,
	},
	{
		'comment': "Really long tracks (eg full albums) are zero weighted",
		'payload': {
			'url': "http://example.com/full-album.mp3",
			'tags': {
				'title': 'The Best of Some Band - Full Album',
			},
			'collections': [],
			'duration': 1912,
		},
		'expected': 0,
	},
	{
		'comment': "Karaoke tracks are zero weighted",
		'payload': {
			'url': "http://example.com/karaoke-track.mp3",
			'tags': {
				'title': 'I Will Survive - Karaoke Backing Track',
			},
			'collections': [
				{
					'slug': 'karaoke',
				},
			],
		},
		'expected': 0,
	},
	{
		'comment': "Soft cap preserves rating ratios: 8 is always 2x a 4",
		'payload_a': {
			'url': "http://example.com/a.mp3",
			'tags': {
				'title': 'Track A',
				'rating': "8",
				'added': "2020-03-04T21:21",
			},
			'collections': [{'slug': 'halloween'}],
		},
		'payload_b': {
			'url': "http://example.com/b.mp3",
			'tags': {
				'title': 'Track B',
				'rating': "4",
				'added': "2020-03-04T21:21",
			},
			'collections': [{'slug': 'halloween'}],
		},
		'datetime': "2020-10-30T12:00",
		'ratio_test': True,
		'expected_ratio': 2.0,
	},
	{
		'comment': "Soft cap function itself: soft_cap(1, 100) ≈ 1",
		'soft_cap_test': True,
		'input': 1,
		'cap': 100,
		'expected': 0.99502,
	},
	{
		'comment': "Soft cap function itself: soft_cap(100, 100) ≈ 63.21",
		'soft_cap_test': True,
		'input': 100,
		'cap': 100,
		'expected': 63.21206,
	},
	{
		'comment': "Soft cap function itself: soft_cap(5000, 100) approaches 100",
		'soft_cap_test': True,
		'input': 5000,
		'cap': 100,
		'expected': 100,
	},
]
failures = 0
for case in testcases:

	# Direct soft_cap function tests
	if case.get('soft_cap_test'):
		actual = soft_cap(case['input'], case['cap'])
		if (round(actual, 5) != round(case['expected'], 5)):
			print("\033[91mFailed\033[0m \"" + case['comment'] + "\".  Returned \033[91m" + str(actual) + "\033[0m, expected " + str(case['expected']))
			failures += 1
		continue

	# Rating ratio preservation tests
	if case.get('ratio_test'):
		currentDateTime = datetime.datetime.fromisoformat(case['datetime'])
		weight_a = getWeighting(case['payload_a'], currentDateTime)
		weight_b = getWeighting(case['payload_b'], currentDateTime)
		actual_ratio = weight_a / weight_b if weight_b != 0 else float('inf')
		if (round(actual_ratio, 5) != round(case['expected_ratio'], 5)):
			print("\033[91mFailed\033[0m \"" + case['comment'] + "\".  Returned ratio \033[91m" + str(actual_ratio) + "\033[0m, expected " + str(case['expected_ratio']))
			failures += 1
		continue

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
