FROM lucas42/lucos_scheduled_scripts:2.0.9
ARG VERSION
ENV VERSION=$VERSION

RUN pip install pipenv

RUN echo "10 2 * * * pipenv run python -u all-tracks.py" | crontab -
COPY startup.sh .

COPY Pipfile* ./
RUN pipenv install

COPY src/* ./

CMD [ "./startup.sh"]