# Media Weighting Script

Updates the lucos media API with a weighting for each track to indicate how likely it should be that a given track gets selected for random playing.

## Factors which affect the weighting of a track

* The rating given to the track
* Non-music formats are less likely to be played (eg podcasts, sound effects)
* Tracks tagged as Christmas tracks are more likely to be played in December and less likely the rest of the year
* Tracks tagged as Halloween are more likely to be played at the end of October

## Testing

Doesn't use a proper testing framework.  However, run
`./test.py`
which will check various calls to the getWeighting() function

## Dependencies

* docker
* docker-compose

## Remote Dependencies

* [lucos_media_metadata_api](https://github.com/lucas42/lucos_media_metadata_api)

## Build-time Dependencies (Installed by Dockerfile)

* [python 3](https://www.python.org/download/releases/3.0/)

## Running
`nice -19 docker-compose up -d --no-build`

## Running script without cron

To test the script logic with worrying about cronjobs.

Set `entrypoint: pipenv run python -u run.py` in the docker-compose file (or equivalent)

## Running locally

Run `pipenv install` to setup

`pipenv run python run.py`


## Environment Variables
For local development, these should be stored in a .env file

* _**MEDIA_API**_ URL of an instance of [lucos_media_metadata_api](https://github.com/lucas42/lucos_media_metadata_api)
* _**PORT**_ The TCP port to the run the HTTP server on.  Defaults to 8023 to avoid clashes with other lucos services.

## File structure

* `Dockerfile`, `Pipfile`, `Pipfile.lock` and the `.cirleci` directory are used at build time
* `src` directory holds the python source code
  - `cron.sh` ensures the cron daemon is running with the right environment set up and sharing its logs in a way that get surfaced to Docker
  - `logic.py` holds the logic for calculating the weighting of a given track.
  - `server.py` runs a HTTP server which updates the weighting of a given track via the metadata API.
  - `all-tracks.py` is script which iterates through all the tracks and updates the weightings via the metadata API.
* `test.py` does some simple checks on the logic in `src/logic.py`.