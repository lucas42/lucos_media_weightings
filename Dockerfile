# The version of pipenv bundled with Debian bookworm doesn't appear to be compatible with python 3.12, so lock at 3.11 for now.
FROM python:3.11

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y pipenv cron

RUN echo "10 2 * * * root cd `pwd` && pipenv run python -u all-tracks.py >> /var/log/cron.log 2>&1" > /etc/cron.d/weighting-all-tracks
COPY startup.sh .

COPY Pipfile* ./
RUN pipenv install

COPY src/* ./

EXPOSE $PORT
CMD [ "./startup.sh"]