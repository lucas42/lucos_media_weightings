#!/bin/bash
# Run the full test suite. All test files live in src/.
set -e
cd "$(dirname "$0")/src"
python3 test_logic.py
python3 test_auth.py
python3 test_webhook.py
python3 test_media_api.py
