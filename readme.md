# Media Weighting Script

Updates the lucos media API with a weighting for each track to indicate how likely it should be that a given track gets selected for random playing.

## Factors which affect the weighting of a track

* The rating given to the track
* Non-music formats are less likely to be played (eg podcasts, sound effects)
* Tracks tagged as Christmas tracks are more likely to be played in December and less likely the rest of the year
* Tracks tagged as Halloween are more likely to be played at the end of October

## Dependencies

* Python

## Running

`./run.py $BASE_URL_OF_MEDIA_API`

## Testing

Doesn't use a proper testing framework.  However, run
`./test.py`
which will check various calls to the getWeighting() function