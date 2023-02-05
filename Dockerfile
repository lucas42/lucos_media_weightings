FROM python:3

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y pipenv cron

RUN echo "10 2 * * * root cd `pwd` && pipenv run python -u run.py >> /var/log/cron.log 2>&1" > /etc/cron.d/weightings
COPY cron.sh .

COPY Pipfile* ./
RUN pipenv install
COPY *.py ./

EXPOSE $PORT
CMD [ "./cron.sh"]