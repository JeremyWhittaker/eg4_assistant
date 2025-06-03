#!/bin/bash
# Run EG4 Assistant server
cd "$(dirname "$0")"
export PYTHONPATH=".."
python app.py