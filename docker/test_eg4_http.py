#!/usr/bin/env python3
"""Test HTTP connection to EG4 18kPV"""

import requests
import json

def test_http_connection():
    """Test HTTP/REST API connection to EG4"""
    host = '172.16.107.129'
    username = 'admin'
    password = 'admin'
    
    # Try common EG4 API endpoints
    endpoints = [
        f'http://{host}/api/system/status',
        f'http://{host}/api/inverter/status',
        f'http://{host}/status',
        f'http://{host}/inverter/status',
        f'http://{host}:80/api/status',
        f'http://{host}:8080/api/status',
    ]
    
    for endpoint in endpoints:
        print(f"\nTrying: {endpoint}")
        try:
            # Try without auth first
            response = requests.get(endpoint, timeout=3)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Success! Response: {response.text[:200]}")
                return
                
            # Try with basic auth
            response = requests.get(endpoint, auth=(username, password), timeout=3)
            print(f"Status with auth: {response.status_code}")
            if response.status_code == 200:
                print(f"Success with auth! Response: {response.text[:200]}")
                return
                
        except requests.exceptions.ConnectionError:
            print("Connection refused")
        except requests.exceptions.Timeout:
            print("Timeout")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_http_connection()