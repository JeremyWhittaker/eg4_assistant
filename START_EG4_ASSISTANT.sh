#!/bin/bash
#
# EG4 Assistant Startup Script
# This starts the EG4 Assistant web server that clones Solar Assistant functionality
#

echo "=============================================="
echo "       EG4 ASSISTANT - SOLAR MONITOR"
echo "=============================================="
echo ""
echo "Web-based monitoring system for EG4 18kPV inverters"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r eg4_assistant/requirements.txt

# Export Python path
export PYTHONPATH="$(pwd)"

# Show configuration
echo ""
echo "Configuration:"
echo "  - EG4 Inverter IP: 172.16.107.53"
echo "  - IoTOS Port: 8000"
echo "  - Web Interface: http://localhost:5000"
echo "  - Live data updates every 5 seconds"
echo ""

# Start the server
echo "Starting EG4 Assistant server..."
echo "Press Ctrl+C to stop"
echo ""

cd eg4_assistant
python app.py