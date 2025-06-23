#!/bin/bash
# Startup script for EG4 Web Monitor

echo "Starting EG4 Web Monitor..."

# Install requirements if not already installed
pip install -r requirements_web.txt

# Make sure playwright browsers are installed
playwright install chromium

# Start the web server on port 8282
echo "Starting web server on port 8282..."
python3 eg4_web_monitor.py