#!/usr/bin/env python3
"""
Simplified Solar Assistant Server for testing
"""

import os
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Test data
test_data = {
    'pv_power': 3500,
    'battery_power': -1200,
    'grid_power': 500,
    'load_power': 2800,
    'battery_soc': 75,
    'pv1_voltage': 380.5,
    'pv1_current': 4.6,
    'battery_voltage': 51.2,
    'grid_voltage': 230.1,
    'grid_frequency': 50.0,
    'inverter_temp': 45.5
}

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'data': test_data,
        'inverters': 1
    })

@app.route('/api/current')
def api_current():
    return jsonify(test_data)

@app.route('/charts')
def charts():
    return render_template('charts.html')

@app.route('/power')
def power():
    return render_template('power.html')

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    socketio.emit('inverter_update', test_data)

@socketio.on('request_update')
def handle_request_update():
    socketio.emit('inverter_update', test_data)

if __name__ == '__main__':
    logger.info('Starting Solar Assistant Test Server on port 5000')
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)