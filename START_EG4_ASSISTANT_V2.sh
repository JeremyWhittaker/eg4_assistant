#!/bin/bash
#
# EG4 Assistant V2 Startup Script
# Enhanced multi-inverter monitoring system
#

echo "=============================================="
echo "     EG4 ASSISTANT V2 - SOLAR MONITOR"
echo "=============================================="
echo ""
echo "Enhanced Features:"
echo "  ✓ Multi-inverter support"
echo "  ✓ Modbus TCP/RTU protocols"
echo "  ✓ MQTT integration"
echo "  ✓ Data persistence with SQLite"
echo "  ✓ CSV/JSON export"
echo "  ✓ Real-time WebSocket updates"
echo "  ✓ Configurable alerts"
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

# Check which version to run
if [ "$1" = "v1" ]; then
    echo "Running original version..."
    cd eg4_assistant
    python app.py
else
    echo "Running enhanced V2..."
    cd eg4_assistant
    python app_v2.py
fi