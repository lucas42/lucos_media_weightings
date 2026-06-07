#!/bin/bash
# Run the full test suite. All test files live in src/.
set -e
cd "$(dirname "$0")/src"
pipenv run python3 test_logic.py
pipenv run python3 test_auth.py
pipenv run python3 test_webhook.py
pipenv run python3 test_media_api.py
pipenv run python3 test_all_tracks.py
