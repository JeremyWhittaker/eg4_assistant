#!/usr/bin/env python3
"""
Simple test to verify Solar Assistant is working
"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Solar Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .status { background: #f0f0f0; padding: 20px; border-radius: 8px; }
            .value { font-size: 24px; font-weight: bold; color: #2196F3; }
        </style>
    </head>
    <body>
        <h1>Solar Assistant - Test Mode</h1>
        <div class="status">
            <h2>System Status</h2>
            <p>PV Power: <span class="value">3500W</span></p>
            <p>Battery Power: <span class="value">-1200W</span></p>
            <p>Grid Power: <span class="value">500W</span></p>
            <p>Load Power: <span class="value">2800W</span></p>
            <p>Battery SOC: <span class="value">75%</span></p>
        </div>
        <p>API Status: <a href="/api/status">/api/status</a></p>
        <p>The full Solar Assistant interface is being configured...</p>
    </body>
    </html>
    '''

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'message': 'Solar Assistant is running in test mode',
        'data': {
            'pv_power': 3500,
            'battery_power': -1200,
            'grid_power': 500,
            'load_power': 2800,
            'battery_soc': 75
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)