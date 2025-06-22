#!/bin/bash
# Run EG4 monitor for 10 updates

echo "Starting EG4 Monitor - 10 updates..."
python3 -u eg4_monitor_stream.py | head -15