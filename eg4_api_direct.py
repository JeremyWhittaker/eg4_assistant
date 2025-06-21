#!/usr/bin/env python3
"""
EG4 API Direct - Try to find and use the API endpoints directly
"""

import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

class EG4APIDirect:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.session = requests.Session()
        self.logged_in = False
        
        # Common headers to appear more like a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': f'{self.base_url}/WManage/web/monitor/inverter'
        })
    
    def login(self):
        """Login to EG4 cloud monitor"""
        try:
            # Get login page for cookies
            login_page_url = f"{self.base_url}/WManage/web/login"
            self.session.get(login_page_url)
            
            # Try login
            login_data = {
                'account': self.username,
                'password': self.password
            }
            
            # Add JSON header for API login
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            response = self.session.post(
                login_page_url,
                data=login_data,
                headers=headers,
                allow_redirects=False
            )
            
            print(f"Login response: {response.status_code}")
            
            # Try JSON login endpoint
            if response.status_code != 200:
                json_login_url = f"{self.base_url}/WManage/api/login"
                headers = {'Content-Type': 'application/json'}
                
                response = self.session.post(
                    json_login_url,
                    json=login_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if result.get('success') or result.get('code') == 0:
                            print("JSON login successful!")
                            self.logged_in = True
                            return True
                    except:
                        pass
            
            self.logged_in = True  # Assume success
            return True
            
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def find_api_endpoints(self):
        """Try to discover API endpoints"""
        if not self.logged_in:
            if not self.login():
                return None
        
        print("\nSearching for API endpoints...")
        
        # Common API endpoint patterns
        endpoints = [
            '/WManage/api/inverter/status',
            '/WManage/api/inverter/realtime',
            '/WManage/api/device/status',
            '/WManage/api/device/realtime',
            '/WManage/api/monitor/data',
            '/WManage/api/monitor/realtime',
            '/WManage/api/data/realtime',
            '/WManage/api/data/current',
            '/WManage/web/monitor/api/data',
            '/WManage/web/monitor/inverter/data',
            '/api/inverter/status',
            '/api/device/realtime',
            '/api/v1/device/realtime',
            '/api/v1/inverter/status',
            '/realtime',
            '/status',
            '/data'
        ]
        
        found_endpoints = []
        
        for endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✓ Found endpoint: {endpoint}")
                    
                    # Try to parse as JSON
                    try:
                        data = response.json()
                        print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                        found_endpoints.append((endpoint, data))
                    except:
                        print(f"  Response (not JSON): {response.text[:100]}...")
                        
                elif response.status_code in [401, 403]:
                    print(f"? Protected endpoint: {endpoint} (status: {response.status_code})")
                    
            except requests.exceptions.Timeout:
                pass
            except Exception as e:
                pass
        
        return found_endpoints
    
    def get_websocket_info(self):
        """Try to find WebSocket endpoints from the main page"""
        try:
            # Get the monitor page
            monitor_url = f"{self.base_url}/WManage/web/monitor/inverter"
            response = self.session.get(monitor_url)
            
            # Look for WebSocket URLs in the JavaScript
            import re
            
            ws_patterns = [
                r'ws://[^"\']+',
                r'wss://[^"\']+',
                r'new WebSocket\(["\']([^"\']+)',
                r'socket.*=.*["\']([^"\']+)',
            ]
            
            print("\nSearching for WebSocket endpoints...")
            
            for pattern in ws_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    print(f"Found WebSocket: {match}")
                    
            # Look for AJAX/fetch calls
            ajax_patterns = [
                r'fetch\(["\']([^"\']+)',
                r'\.ajax\({[^}]*url:\s*["\']([^"\']+)',
                r'axios\.[get|post]+\(["\']([^"\']+)',
                r'\.get\(["\']([^"\']+)',
                r'\.post\(["\']([^"\']+)'
            ]
            
            print("\nSearching for AJAX endpoints...")
            
            for pattern in ajax_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches[:10]:  # Limit output
                    if match and not match.startswith('http') and not match.startswith('//'):
                        print(f"Found AJAX endpoint: {match}")
                        
        except Exception as e:
            print(f"Error finding endpoints: {e}")
    
    def try_graphql(self):
        """Try GraphQL endpoint"""
        graphql_endpoints = [
            '/graphql',
            '/api/graphql',
            '/WManage/graphql',
            '/WManage/api/graphql'
        ]
        
        query = """
        {
            inverter {
                batterySoc
                batteryPower
                gridPower
                pvPower
                loadPower
            }
        }
        """
        
        print("\nTrying GraphQL endpoints...")
        
        for endpoint in graphql_endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                response = self.session.post(
                    url,
                    json={'query': query},
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    print(f"✓ GraphQL endpoint found: {endpoint}")
                    data = response.json()
                    print(f"Response: {json.dumps(data, indent=2)}")
                    return data
                    
            except:
                pass
                
        return None

if __name__ == "__main__":
    api = EG4APIDirect()
    
    print("EG4 API Direct Discovery")
    print("="*50)
    
    # Try to login
    if api.login():
        # Search for API endpoints
        endpoints = api.find_api_endpoints()
        
        # Look for WebSocket info
        api.get_websocket_info()
        
        # Try GraphQL
        api.try_graphql()
        
        if endpoints:
            print(f"\nFound {len(endpoints)} working endpoints")
            print("\nTo use these endpoints in your own code:")
            print("1. Login first to get session cookies")
            print("2. Use the session to access the endpoints")
            print("3. Parse the JSON response for the data you need")
        else:
            print("\nNo direct API endpoints found")
            print("The site likely uses WebSocket or requires JavaScript")
            print("You may need to use Selenium or Playwright for browser automation")