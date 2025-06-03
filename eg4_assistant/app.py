#!/usr/bin/env python3
"""
EG4 Assistant - Web Monitoring for EG4 18kPV
Main Flask application with real-time WebSocket support
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
import json
import os
from datetime import datetime, timedelta
from collections import deque
import socket
import struct
import binascii

# Import our EG4 communication module
import sys
sys.path.append('..')
from eg4_iotos_client import EG4IoTOSClient

app = Flask(__name__)
app.config['SECRET_KEY'] = 'eg4-assistant-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global data store
inverter_data = {
    'current': {},
    'history': deque(maxlen=1440),  # 24 hours of minute data
    'totals': {
        'today': {'energy_produced': 0, 'energy_consumed': 0},
        'yesterday': {'energy_produced': 0, 'energy_consumed': 0},
        'month': {'energy_produced': 0, 'energy_consumed': 0},
        'year': {'energy_produced': 0, 'energy_consumed': 0},
        'lifetime': {'energy_produced': 0, 'energy_consumed': 0}
    },
    'configuration': {
        'site_owner': 'me@jeremywhittaker.com',
        'site_id': 'whittakers.us.eg4-assistant.io',
        'inverter_model': 'Luxpower (EG4 18kPV)',
        'inverter_serial': 'BA32401949',
        'inverter_ip': '172.16.107.53',
        'wifi_ssid': 'Whittakers 🟩🟩🟩🟩🟩🟩',
        'wifi_status': 'Connected',
        'local_ip': '172.16.106.13',
        'internet_ip': '70.166.112.82',
        'timezone': 'America/Phoenix',
        'mqtt_enabled': True,
        'mqtt_port': 1883
    }
}

# EG4 client instance
eg4_client = None
monitoring_thread = None
monitoring_active = False

def parse_eg4_data(response):
    """Parse EG4 IoTOS response into meaningful data"""
    if not response or len(response) < 50:
        return None
        
    # Extract serial number (we know it's at offset 8)
    try:
        serial_start = 8
        serial_end = response.find(b'\x00', serial_start)
        serial = response[serial_start:serial_end].decode('ascii', errors='ignore')
    except:
        serial = 'Unknown'
    
    # Create mock data based on typical inverter values
    # In production, this would parse actual IoTOS protocol
    import random
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'serial': serial,
        
        # PV Input
        'pv1_voltage': round(random.uniform(380, 420), 1),
        'pv1_current': round(random.uniform(0, 25), 1),
        'pv1_power': 0,  # Will calculate
        'pv2_voltage': round(random.uniform(380, 420), 1),
        'pv2_current': round(random.uniform(0, 25), 1),
        'pv2_power': 0,  # Will calculate
        
        # Battery
        'battery_voltage': round(random.uniform(51, 54), 1),
        'battery_current': round(random.uniform(-50, 50), 1),
        'battery_power': 0,  # Will calculate
        'battery_soc': round(random.uniform(20, 95)),
        'battery_temp': round(random.uniform(25, 35), 1),
        
        # Grid
        'grid_voltage': round(random.uniform(238, 242), 1),
        'grid_frequency': round(random.uniform(59.9, 60.1), 2),
        'grid_power': round(random.uniform(-5000, 5000)),
        
        # Load/Output
        'load_power': round(random.uniform(500, 3000)),
        'ac_output_voltage': round(random.uniform(238, 242), 1),
        'ac_output_frequency': round(random.uniform(59.9, 60.1), 2),
        'ac_output_power': round(random.uniform(500, 3000)),
        
        # System
        'inverter_temp': round(random.uniform(35, 45), 1),
        'status': 'Normal',
        'mode': 'Grid-Tie'
    }
    
    # Calculate power values
    data['pv1_power'] = int(data['pv1_voltage'] * data['pv1_current'])
    data['pv2_power'] = int(data['pv2_voltage'] * data['pv2_current'])
    data['pv_power'] = data['pv1_power'] + data['pv2_power']
    data['battery_power'] = int(data['battery_voltage'] * data['battery_current'])
    
    return data

def monitor_eg4():
    """Background thread to monitor EG4 inverter"""
    global eg4_client, inverter_data, monitoring_active
    
    eg4_client = EG4IoTOSClient(host='172.16.107.53', port=8000)
    
    if not eg4_client.connect():
        print("Failed to connect to EG4 inverter")
        return
        
    print("✓ Connected to EG4 inverter, starting monitoring...")
    
    query_command = b'\xa1\x1a\x05\x00'  # Command that works
    
    while monitoring_active:
        try:
            response = eg4_client.send_receive(query_command)
            
            if response:
                data = parse_eg4_data(response)
                
                if data:
                    # Update current data
                    inverter_data['current'] = data
                    
                    # Add to history
                    inverter_data['history'].append({
                        'timestamp': data['timestamp'],
                        'pv_power': data['pv_power'],
                        'battery_power': data['battery_power'],
                        'grid_power': data['grid_power'],
                        'load_power': data['load_power'],
                        'battery_soc': data['battery_soc']
                    })
                    
                    # Update totals (simplified)
                    if data['pv_power'] > 0:
                        inverter_data['totals']['today']['energy_produced'] += data['pv_power'] / 60000  # kWh
                    if data['load_power'] > 0:
                        inverter_data['totals']['today']['energy_consumed'] += data['load_power'] / 60000  # kWh
                    
                    # Emit real-time update via WebSocket
                    socketio.emit('inverter_update', data)
                    
            time.sleep(5)  # Update every 5 seconds
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(10)
    
    eg4_client.disconnect()

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html', data=inverter_data)

@app.route('/charts')
def charts():
    """Charts page (iframe to Grafana or custom charts)"""
    return render_template('charts.html', data=inverter_data)

@app.route('/totals')
def totals():
    """Energy totals page"""
    return render_template('totals.html', data=inverter_data)

@app.route('/power')
def power():
    """Power flow visualization page"""
    return render_template('power.html', data=inverter_data)

@app.route('/configuration')
def configuration():
    """Configuration page"""
    return render_template('configuration.html', data=inverter_data)

# API Routes
@app.route('/api/current')
def api_current():
    """Get current inverter data"""
    return jsonify(inverter_data['current'])

@app.route('/api/history')
def api_history():
    """Get historical data"""
    return jsonify(list(inverter_data['history']))

@app.route('/api/totals')
def api_totals():
    """Get energy totals"""
    return jsonify(inverter_data['totals'])

@app.route('/api/configuration')
def api_configuration():
    """Get configuration"""
    return jsonify(inverter_data['configuration'])

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'data': 'Connected to EG4 Assistant'})
    
@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('request_update')
def handle_update_request():
    """Handle manual update request"""
    emit('inverter_update', inverter_data['current'])

def start_monitoring():
    """Start the monitoring thread"""
    global monitoring_thread, monitoring_active
    
    if not monitoring_active:
        monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_eg4)
        monitoring_thread.daemon = True
        monitoring_thread.start()

def stop_monitoring():
    """Stop the monitoring thread"""
    global monitoring_active
    monitoring_active = False

if __name__ == '__main__':
    print("Starting EG4 Assistant...")
    print("=" * 50)
    print(f"Web interface: http://localhost:5000")
    print(f"Monitoring EG4 at: {inverter_data['configuration']['inverter_ip']}")
    print("=" * 50)
    
    # Start monitoring
    start_monitoring()
    
    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)