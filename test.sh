#!/bin/bash

set -e

echo "Running tests..."
if [ -f venv/bin/activate ]; then
  source venv/bin/activate
fi
pytest "$@" 