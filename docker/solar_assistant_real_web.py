#!/usr/bin/env python3
"""
Solar Assistant Web Interface with Real Data ONLY
No fake values - displays real data or errors
"""

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json
import os
import time
from datetime import datetime
import threading
from real_data_collector import RealDataCollector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'solar_assistant_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Add abs function to Jinja2 environment
app.jinja_env.globals.update(abs=abs)
app.jinja_env.filters['abs'] = abs

# Initialize real data collector
real_collector = RealDataCollector()
real_collector.start()

# Global data store
current_data = {}

def update_data():
    """Update current_data with real values from Solar Assistant"""
    global current_data
    
    # Get real data
    real_data = real_collector.get_data()
    
    if real_data and not real_data.get('error'):
        # We have real data!
        current_data = {
            'timestamp': real_data.get('timestamp', datetime.now().isoformat()),
            'connected': True,
            'battery': {
                'soc': real_data.get('battery_soc', {}).get('value', 0),
                'voltage': real_data.get('battery_voltage', {}).get('value', 0),
                'current': real_data.get('battery_current', {}).get('value', 0),
                'power': real_data.get('battery_power', {}).get('value', 0),
                'temp': real_data.get('battery_temp', {}).get('value', 0),
                'status': real_data.get('battery_status', 'unknown')
            },
            'grid': {
                'voltage': real_data.get('grid_voltage', {}).get('value', 0),
                'frequency': real_data.get('grid_frequency', {}).get('value', 0),
                'power': real_data.get('grid_power', {}).get('value', 0)
            },
            'pv': {
                'power': real_data.get('pv_power', {}).get('value', 0),
                'pv1_power': real_data.get('pv1_power', {}).get('value', 0),
                'pv2_power': real_data.get('pv2_power', {}).get('value', 0),
                'pv1_voltage': real_data.get('pv1_voltage', {}).get('value', 0),
                'pv2_voltage': real_data.get('pv2_voltage', {}).get('value', 0)
            },
            'load': {
                'power': real_data.get('load_power', {}).get('value', 0),
                'essential': real_data.get('load_power_essential', {}).get('value', 0),
                'nonessential': real_data.get('load_power_nonessential', {}).get('value', 0)
            },
            'inverter': {
                'temp': real_data.get('inverter_temp', {}).get('value', 0),
                'ac_output_voltage': real_data.get('ac_output_voltage', {}).get('value', 0),
                'mode': real_data.get('system_mode', 'Unknown')
            }
        }
    else:
        # Error or no data
        current_data = {
            'timestamp': datetime.now().isoformat(),
            'connected': False,
            'error': real_data.get('error', 'Cannot connect to Solar Assistant at 172.16.109.214')
        }

def data_updater():
    """Background thread to update data and emit to clients"""
    while True:
        try:
            update_data()
            socketio.emit('data_update', current_data)
        except Exception as e:
            logger.error(f"Error in data updater: {e}")
        time.sleep(5)

@app.route('/')
def index():
    """Main page - shows real data or error"""
    update_data()  # Get fresh data
    return render_template('real_dashboard.html', data=current_data)

@app.route('/api/data')
def api_data():
    """API endpoint for current data"""
    update_data()  # Get fresh data
    return jsonify(current_data)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    update_data()
    emit('data_update', current_data)

if __name__ == '__main__':
    # Start data updater thread
    updater_thread = threading.Thread(target=data_updater)
    updater_thread.daemon = True
    updater_thread.start()
    
    # Run the app
    port = int(os.environ.get('PORT', 8504))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)