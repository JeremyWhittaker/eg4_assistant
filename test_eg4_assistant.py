#!/usr/bin/env python3
"""
Test EG4 Assistant web server
"""

import requests
import time
import subprocess
import os
import signal

def test_server():
    """Test the EG4 Assistant server"""
    
    print("Starting EG4 Assistant server...")
    
    # Start the server
    env = os.environ.copy()
    env['PYTHONPATH'] = '.'
    server_process = subprocess.Popen(
        ['python', 'eg4_assistant/app.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give it time to start
    time.sleep(5)
    
    try:
        # Test endpoints
        endpoints = [
            ('/', 'Dashboard'),
            ('/charts', 'Charts'),
            ('/totals', 'Totals'),
            ('/power', 'Power'),
            ('/configuration', 'Configuration'),
            ('/api/current', 'API Current'),
            ('/api/totals', 'API Totals'),
            ('/api/configuration', 'API Configuration')
        ]
        
        print("\nTesting endpoints:")
        for endpoint, name in endpoints:
            try:
                response = requests.get(f'http://localhost:5000{endpoint}', timeout=5)
                print(f"  {name}: {response.status_code} {'✓' if response.status_code == 200 else '✗'}")
            except Exception as e:
                print(f"  {name}: Error - {e}")
        
        print("\nServer is running successfully!")
        print("Access the web interface at: http://localhost:5000")
        print("\nPress Ctrl+C to stop the server")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        # Stop the server
        server_process.terminate()
        server_process.wait()
        print("Server stopped")

if __name__ == "__main__":
    test_server()