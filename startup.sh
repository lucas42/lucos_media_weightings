#!/bin/sh
set -e

supercronic /crontab &
pipenv run python -u server.py
