FROM python:3.15.0a5-alpine

WORKDIR /usr/src/app

RUN pip install pipenv

RUN echo "10 2 * * * cd `pwd` && pipenv run python -u all-tracks.py >> /var/log/cron.log 2>&1" | crontab -
COPY startup.sh .

COPY Pipfile* ./
RUN pipenv install

COPY src/* ./

CMD [ "./startup.sh"]