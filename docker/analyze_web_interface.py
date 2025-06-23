#!/usr/bin/env python3
import requests
import json
import time
import websocket
from urllib.parse import urlparse

# Solar Assistant URL
BASE_URL = "http://172.16.106.13"

# Session to maintain cookies
session = requests.Session()

def analyze_main_page():
    """Analyze the main page and extract data"""
    print("=== Analyzing Main Page ===")
    
    try:
        # Get the main page
        response = session.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Cookies: {session.cookies.get_dict()}")
        
        # Look for WebSocket URL or API endpoints
        if 'data-phx-' in response.text:
            print("\nPhoenix LiveView detected!")
            
        # Look for data values in the HTML
        if 'Battery state of charge' in response.text:
            print("\nBattery data found in HTML")
            
        # Save the HTML for analysis
        with open('/home/jeremy/src/solar_assistant/docker/solar_assistant_main_page.html', 'w') as f:
            f.write(response.text)
            
        print("\nMain page HTML saved to solar_assistant_main_page.html")
        
        # Extract CSRF token
        csrf_token = None
        if 'csrf-token' in response.text:
            import re
            match = re.search(r'name="csrf-token" content="([^"]+)"', response.text)
            if match:
                csrf_token = match.group(1)
                print(f"CSRF Token: {csrf_token}")
                
        return csrf_token
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def analyze_websocket():
    """Analyze WebSocket connections"""
    print("\n=== Analyzing WebSocket ===")
    
    # Check for Phoenix LiveView WebSocket
    ws_url = f"ws://172.16.106.13/live/websocket?_csrf_token=&vsn=2.0.0"
    print(f"Attempting WebSocket connection to: {ws_url}")
    
    try:
        # Note: This is a simplified test - Phoenix LiveView has complex protocol
        headers = {
            "Origin": BASE_URL,
            "Cookie": "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
        }
        
        ws = websocket.WebSocket()
        ws.connect(ws_url, header=headers)
        print("WebSocket connected!")
        
        # Send a Phoenix heartbeat
        ws.send('[null,"1","phoenix","heartbeat",{}]')
        
        # Read response
        result = ws.recv()
        print(f"WebSocket response: {result}")
        
        ws.close()
        
    except Exception as e:
        print(f"WebSocket error: {e}")

def check_api_endpoints():
    """Check for API endpoints"""
    print("\n=== Checking API Endpoints ===")
    
    # Common API endpoints to check
    endpoints = [
        "/api/stats",
        "/api/data",
        "/api/inverter",
        "/api/battery",
        "/api/solar",
        "/api/grid",
        "/api/load",
        "/stats",
        "/data",
        "/inverter/data",
        "/battery/data",
        "/live/stats"
    ]
    
    for endpoint in endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.status_code != 404:
                print(f"{endpoint}: {response.status_code}")
                if response.status_code == 200:
                    print(f"  Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                    if 'json' in response.headers.get('Content-Type', ''):
                        print(f"  Data: {response.text[:200]}...")
        except Exception as e:
            print(f"{endpoint}: Error - {e}")

def check_grafana_api():
    """Check if Grafana API is accessible"""
    print("\n=== Checking Grafana API ===")
    
    grafana_endpoints = [
        "/grafana/api/datasources",
        "/grafana/api/dashboards",
        "/api/datasources/proxy/1/query",
        "/d/dashboard/solar-assistant"
    ]
    
    for endpoint in grafana_endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}", timeout=5)
            print(f"{endpoint}: {response.status_code}")
        except Exception as e:
            print(f"{endpoint}: Error - {e}")

def check_influxdb_query():
    """Check if we can query InfluxDB directly"""
    print("\n=== Checking InfluxDB Direct Access ===")
    
    # InfluxDB might be on port 8086
    try:
        response = requests.get("http://172.16.106.13:8086/query?db=solar_assistant&q=SHOW MEASUREMENTS", timeout=5)
        print(f"InfluxDB direct access: {response.status_code}")
        if response.status_code == 200:
            print(f"Data: {response.text[:200]}...")
    except Exception as e:
        print(f"InfluxDB error: {e}")

if __name__ == "__main__":
    print("Solar Assistant Web Interface Analysis")
    print("=" * 50)
    
    # Analyze main page
    csrf_token = analyze_main_page()
    
    # Check API endpoints
    check_api_endpoints()
    
    # Check WebSocket
    analyze_websocket()
    
    # Check Grafana
    check_grafana_api()
    
    # Check InfluxDB
    check_influxdb_query()