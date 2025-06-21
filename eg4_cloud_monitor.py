#!/usr/bin/env python3
"""
EG4 Cloud Monitor - Get live statistics from monitor.eg4electronics.com
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()

class EG4CloudMonitor:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.session = requests.Session()
        self.logged_in = False
        
    def login(self):
        """Login to EG4 cloud monitor"""
        try:
            # First, get the login page to obtain any tokens
            login_page_url = f"{self.base_url}/WManage/web/login"
            print(f"Getting login page: {login_page_url}")
            
            login_page = self.session.get(login_page_url)
            login_page.raise_for_status()
            
            # Parse for any CSRF tokens or form data
            soup = BeautifulSoup(login_page.text, 'html.parser')
            
            # Look for hidden form fields
            form = soup.find('form')
            hidden_fields = {}
            if form:
                for hidden in form.find_all('input', type='hidden'):
                    if hidden.get('name') and hidden.get('value'):
                        hidden_fields[hidden['name']] = hidden['value']
            
            # Prepare login data - EG4 uses 'account' not 'username'
            login_data = {
                'account': self.username,
                'password': self.password,
                **hidden_fields
            }
            
            # Common variations of login field names
            possible_username_fields = ['username', 'user', 'email', 'account', 'loginId']
            possible_password_fields = ['password', 'pass', 'pwd']
            
            # Try to find actual field names from form
            if form:
                username_input = form.find('input', {'type': ['text', 'email']})
                password_input = form.find('input', {'type': 'password'})
                
                if username_input and username_input.get('name'):
                    # Clear other username attempts
                    for field in possible_username_fields:
                        login_data.pop(field, None)
                    login_data[username_input['name']] = self.username
                    
                if password_input and password_input.get('name'):
                    # Clear other password attempts
                    for field in possible_password_fields:
                        login_data.pop(field, None)
                    login_data[password_input['name']] = self.password
            
            # Try to find login endpoint
            login_endpoints = [
                '/WManage/web/login',
                '/WManage/login',
                '/login',
                '/api/login',
                '/user/login'
            ]
            
            for endpoint in login_endpoints:
                login_url = f"{self.base_url}{endpoint}"
                print(f"Trying login at: {login_url}")
                
                response = self.session.post(login_url, data=login_data, allow_redirects=False)
                
                # Check if login was successful
                if response.status_code in [200, 302, 303]:
                    # Check for success indicators
                    if response.cookies or 'location' in response.headers:
                        print("Login successful!")
                        self.logged_in = True
                        
                        # Follow redirect if needed
                        if response.status_code in [302, 303]:
                            redirect_url = response.headers.get('location')
                            if redirect_url:
                                if not redirect_url.startswith('http'):
                                    redirect_url = f"{self.base_url}{redirect_url}"
                                self.session.get(redirect_url)
                        
                        return True
            
            print("Login failed - trying alternate method")
            return False
            
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def get_live_data(self):
        """Get live statistics from the monitor page"""
        if not self.logged_in:
            print("Not logged in, attempting login...")
            if not self.login():
                return None
        
        try:
            # Get the monitor page
            monitor_url = f"{self.base_url}/WManage/web/monitor/inverter"
            print(f"Getting monitor page: {monitor_url}")
            
            response = self.session.get(monitor_url)
            response.raise_for_status()
            
            # Parse the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {}
            
            # Look for battery SOC
            soc_element = soup.find('strong', class_='socText')
            if not soc_element:
                # Try alternate selectors
                soc_element = soup.find('p', class_='socHolder')
                if soc_element:
                    soc_text = soc_element.get_text()
                    soc_match = re.search(r'(\d+)%', soc_text)
                    if soc_match:
                        data['battery_soc'] = int(soc_match.group(1))
            else:
                soc_text = soc_element.get_text().strip()
                if soc_text.isdigit():
                    data['battery_soc'] = int(soc_text)
            
            # Look for other common data elements
            # Power values often in elements with class like 'monitorDataText', 'dataValue', etc.
            data_elements = soup.find_all(class_=re.compile('monitorDataText|dataValue|monitorText'))
            
            for elem in data_elements:
                text = elem.get_text().strip()
                parent = elem.parent
                
                # Try to identify what this value represents
                if parent:
                    label_text = parent.get_text().lower()
                    
                    # Parse based on common patterns
                    if 'battery' in label_text and 'power' in label_text:
                        value = self._extract_number(text)
                        if value is not None:
                            data['battery_power'] = value
                    elif 'grid' in label_text and 'power' in label_text:
                        value = self._extract_number(text)
                        if value is not None:
                            data['grid_power'] = value
                    elif 'pv' in label_text or 'solar' in label_text:
                        value = self._extract_number(text)
                        if value is not None:
                            data['pv_power'] = value
                    elif 'load' in label_text:
                        value = self._extract_number(text)
                        if value is not None:
                            data['load_power'] = value
            
            # Also check for JSON data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for JSON patterns
                    json_matches = re.findall(r'\{[^{}]*"(?:soc|battery|power|grid|pv|solar)"[^{}]*\}', script.string)
                    for match in json_matches:
                        try:
                            json_data = json.loads(match)
                            data.update(self._extract_values_from_json(json_data))
                        except:
                            pass
            
            return data
            
        except Exception as e:
            print(f"Error getting live data: {e}")
            self.logged_in = False  # Reset login status
            return None
    
    def _extract_number(self, text):
        """Extract numeric value from text"""
        # Remove commas and find numbers
        text = text.replace(',', '')
        match = re.search(r'-?\d+\.?\d*', text)
        if match:
            try:
                if '.' in match.group():
                    return float(match.group())
                else:
                    return int(match.group())
            except:
                pass
        return None
    
    def _extract_values_from_json(self, json_data):
        """Extract relevant values from JSON data"""
        extracted = {}
        
        key_mappings = {
            'soc': 'battery_soc',
            'batterySoc': 'battery_soc',
            'batteryPower': 'battery_power',
            'gridPower': 'grid_power',
            'pvPower': 'pv_power',
            'solarPower': 'pv_power',
            'loadPower': 'load_power'
        }
        
        for key, value in json_data.items():
            if key in key_mappings and isinstance(value, (int, float)):
                extracted[key_mappings[key]] = value
                
        return extracted
    
    def display_data(self, data):
        """Display the collected data"""
        print(f"\n{'='*60}")
        print(f"EG4 Cloud Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if not data:
            print("No data available")
            return
        
        if 'battery_soc' in data:
            print(f"\nBattery SOC: {data['battery_soc']}%")
        
        if 'battery_power' in data:
            print(f"Battery Power: {data['battery_power']} W")
            
        if 'grid_power' in data:
            print(f"Grid Power: {data['grid_power']} W")
            
        if 'pv_power' in data:
            print(f"PV Power: {data['pv_power']} W")
            
        if 'load_power' in data:
            print(f"Load Power: {data['load_power']} W")
        
        print(f"\nTotal fields retrieved: {len(data)}")
    
    def run_continuous(self, interval=60):
        """Run continuous monitoring"""
        print("EG4 Cloud Monitor")
        print("Monitoring live statistics from monitor.eg4electronics.com")
        print(f"Update interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                data = self.get_live_data()
                self.display_data(data)
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\nStopping monitor...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)

if __name__ == "__main__":
    monitor = EG4CloudMonitor()
    
    # Test single fetch
    print("Testing EG4 cloud monitor connection...")
    data = monitor.get_live_data()
    
    if data:
        monitor.display_data(data)
        print("\n✓ Successfully retrieved data from EG4 cloud!")
        print("\nStarting continuous monitoring...")
        time.sleep(2)
        monitor.run_continuous(interval=30)  # Update every 30 seconds
    else:
        print("\n✗ Failed to retrieve data")
        print("Please check:")
        print("1. Username and password are correct")
        print("2. Internet connection is working")
        print("3. The website structure hasn't changed")