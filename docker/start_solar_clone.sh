#!/bin/bash

echo "Starting Solar Assistant Clone..."

# Ensure InfluxDB is running
if ! pgrep -x "influxd" > /dev/null; then
    echo "Starting InfluxDB..."
    sudo systemctl start influxdb || influxd &
fi

# Install requirements if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# Create templates directory if it doesn't exist
mkdir -p templates

# Run the Solar Assistant Clone
echo "Starting web server on http://0.0.0.0:8500"
python3 solar_assistant_clone.py