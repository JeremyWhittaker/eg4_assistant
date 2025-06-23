#!/usr/bin/env python3
"""
Simple Solar Assistant Web Interface - REAL DATA ONLY
Shows actual values from Solar Assistant at 172.16.109.214
"""

from flask import Flask, jsonify
import json
import os
from datetime import datetime
from real_data_collector import RealDataCollector

app = Flask(__name__)

# Initialize real data collector
collector = RealDataCollector()

@app.route('/')
def index():
    """Simple JSON display of current data"""
    # Get real data
    if collector.collect_data():
        data = collector.get_data()
        return f"""
<html>
<head>
    <title>Solar Assistant - Real Data</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: monospace; background: #f0f0f0; padding: 20px; }}
        .container {{ background: white; padding: 20px; border-radius: 8px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .data {{ white-space: pre-wrap; }}
        .error {{ color: red; font-weight: bold; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Solar Assistant - Real Data from 172.16.109.214</h1>
        <div class="data">{json.dumps(data, indent=2)}</div>
        <div class="timestamp">Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
</body>
</html>
"""
    else:
        return f"""
<html>
<head>
    <title>Solar Assistant - Error</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: monospace; background: #f0f0f0; padding: 20px; }}
        .container {{ background: white; padding: 20px; border-radius: 8px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .error {{ color: red; font-weight: bold; padding: 20px; background: #fee; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Solar Assistant - Connection Error</h1>
        <div class="error">Cannot connect to Solar Assistant at 172.16.109.214<br><br>Error: {collector.error}</div>
    </div>
</body>
</html>
"""

@app.route('/api/data')
def api_data():
    """API endpoint for current data"""
    if collector.collect_data():
        return jsonify(collector.get_data())
    else:
        return jsonify({"error": collector.error}), 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)