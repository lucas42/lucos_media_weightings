# Media Weighting Script

Updates the lucos media API with a weighting for each track to indicate how likely it should be that a given track gets selected for random playing.

## Factors which affect the weighting of a track

* The rating given to the track
* Non-music formats are less likely to be played (eg podcasts, sound effects)
* Tracks tagged as Christmas tracks are more likely to be played in December and less likely the rest of the year
* Tracks tagged as Halloween are more likely to be played at the end of October

## Testing

Run the full test suite with:

```
./run_tests.sh
```

All test files live in `src/`:

| File | What it tests |
|---|---|
| `test_logic.py` | Weighting calculations in `logic.py` |
| `test_auth.py` | Authentication middleware in `server.py` |
| `test_webhook.py` | Webhook handler in `server.py` |
| `test_media_api.py` | SSRF guard and redirect handling in `media_api.py` |

## Dependencies

* docker
* docker compose

## Remote Dependencies

* [lucos_media_metadata_api](https://github.com/lucas42/lucos_media_metadata_api)

## Build-time Dependencies (Installed by Dockerfile)

* [python 3](https://www.python.org/download/releases/3.0/)

## Running
`nice -19 docker compose up -d --no-build`

## Running script without cron

To test the script logic with worrying about cronjobs.

Set `entrypoint: pipenv run python -u all-tracks.py` in the docker compose file (or equivalent)

## Running locally

Run `pipenv install` to setup

`pipenv run python all-tracks.py`


## Environment Variables
For local development, these should be stored in a .env file

* _**MEDIA_API**_ URL of an instance of [lucos_media_metadata_api](https://github.com/lucas42/lucos_media_metadata_api)
* _**PORT**_ The TCP port to the run the HTTP server on.

## File structure

* `Dockerfile`, `Pipfile`, `Pipfile.lock` and the `.circleci` directory are used at build time
* `src` directory holds the python source code and tests
  - `logic.py` holds the logic for calculating the weighting of a given track.
  - `server.py` runs a HTTP server which updates the weighting of a given track via the metadata API.
  - `media_api.py` communicates with the media metadata API.
  - `all-tracks.py` is a script which iterates through all the tracks and updates the weightings via the metadata API.
  - `test_logic.py`, `test_auth.py`, `test_webhook.py`, `test_media_api.py` are the test files.
* `run_tests.sh` runs the full test suite.
* `startup.sh` ensures the cron daemon is running with the right environment set up and sharing its logs in a way that get surfaced to Docker