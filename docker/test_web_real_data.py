#!/usr/bin/env python3
"""Test web interface with real data"""

import os
import time
import threading
import requests
from solar_assistant_web import app, socketio, real_collector

def test_web_interface():
    print("Starting Solar Assistant Web Interface with Real Data")
    print("="*50)
    
    # Start the web server in a thread
    def run_server():
        socketio.run(app, host='0.0.0.0', port=8503, debug=False, allow_unsafe_werkzeug=True)
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    print("Web interface started on http://localhost:8503")
    print("Waiting for real data...")
    
    # Test API endpoint
    for i in range(5):
        time.sleep(5)
        try:
            response = requests.get('http://localhost:8503/api/data')
            data = response.json()
            
            print(f"\nUpdate {i+1}:")
            print("-"*30)
            
            if data.get('error'):
                print(f"Error: {data['error']}")
            else:
                battery = data.get('battery', {})
                grid = data.get('grid', {})
                pv = data.get('pv', {})
                load = data.get('load', {})
                inverter = data.get('inverter', {})
                
                print(f"System Mode: {inverter.get('status', 'Unknown')}")
                print(f"Battery SOC: {battery.get('soc', 0)}%")
                print(f"Battery Power: {battery.get('power', 0)}W ({battery.get('status', 'unknown')})")
                print(f"Grid Power: {grid.get('power', 0)}W")
                print(f"PV Power: {pv.get('power', 0)}W")
                print(f"Load Power: {load.get('power', 0)}W")
                
        except Exception as e:
            print(f"Error getting data: {e}")
    
    print("\n\nWeb interface is running with real data!")
    print("Visit http://localhost:8503 to see the dashboard")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        real_collector.stop()

if __name__ == "__main__":
    test_web_interface()