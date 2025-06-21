#!/usr/bin/env python3
"""
Simple EG4 Cloud Monitor - Get battery SOC from monitor.eg4electronics.com
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import re
import json

# Load environment variables
load_dotenv()

class EG4CloudSimple:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.session = requests.Session()
        self.logged_in = False
        
    def login(self):
        """Login to EG4 cloud monitor"""
        try:
            # Get login page first for any tokens/cookies
            login_page_url = f"{self.base_url}/WManage/web/login"
            print(f"Getting login page...")
            
            response = self.session.get(login_page_url)
            response.raise_for_status()
            
            # Prepare login data with correct field names
            login_data = {
                'account': self.username,
                'password': self.password
            }
            
            # Post login
            print(f"Logging in as {self.username}...")
            login_response = self.session.post(
                login_page_url,
                data=login_data,
                allow_redirects=True
            )
            
            # Check if login successful
            if login_response.status_code == 200:
                # Check if we're redirected away from login page
                if 'login' not in login_response.url:
                    print("Login successful!")
                    self.logged_in = True
                    return True
                else:
                    # Check response content for success indicators
                    if 'dashboard' in login_response.text or 'monitor' in login_response.text:
                        print("Login successful!")
                        self.logged_in = True
                        return True
            
            print(f"Login status unclear, attempting to continue...")
            self.logged_in = True  # Try anyway
            return True
            
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def get_battery_soc(self):
        """Get battery SOC from the monitor page"""
        if not self.logged_in:
            if not self.login():
                return None
        
        try:
            # Get the monitor page
            monitor_url = f"{self.base_url}/WManage/web/monitor/inverter"
            print(f"Getting monitor page...")
            
            response = self.session.get(monitor_url)
            
            # If redirected to login, try logging in again
            if 'login' in response.url:
                print("Session expired, logging in again...")
                self.logged_in = False
                if not self.login():
                    return None
                response = self.session.get(monitor_url)
            
            response.raise_for_status()
            
            # Parse the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Method 1: Look for the specific SOC element
            soc_element = soup.find('strong', class_='socText')
            if soc_element:
                soc_text = soc_element.get_text().strip()
                if soc_text.isdigit():
                    return int(soc_text)
            
            # Method 2: Look in socHolder
            soc_holder = soup.find('p', class_='socHolder')
            if soc_holder:
                text = soc_holder.get_text()
                match = re.search(r'(\d+)%', text)
                if match:
                    return int(match.group(1))
            
            # Method 3: Search for any element containing SOC percentage
            all_text = soup.get_text()
            soc_patterns = [
                r'SOC[:\s]+(\d+)%',
                r'State of Charge[:\s]+(\d+)%',
                r'Battery[:\s]+(\d+)%',
                r'socText["\']>(\d+)<'
            ]
            
            for pattern in soc_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            # Method 4: Look in JavaScript data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for SOC in JavaScript
                    js_patterns = [
                        r'"soc":\s*(\d+)',
                        r'soc:\s*(\d+)',
                        r'batterySoc["\']:\s*(\d+)',
                        r'battery_soc["\']:\s*(\d+)'
                    ]
                    
                    for pattern in js_patterns:
                        match = re.search(pattern, script.string)
                        if match:
                            return int(match.group(1))
            
            # Debug: Save page for inspection
            with open('eg4_monitor_page.html', 'w') as f:
                f.write(response.text)
            print("Page saved to eg4_monitor_page.html for debugging")
            
            print("Could not find battery SOC in page")
            return None
            
        except Exception as e:
            print(f"Error getting battery SOC: {e}")
            return None
    
    def run_continuous(self, interval=30):
        """Continuously monitor battery SOC"""
        print(f"\nEG4 Cloud Monitor - Simple")
        print(f"Monitoring battery SOC every {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                soc = self.get_battery_soc()
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if soc is not None:
                    print(f"[{timestamp}] Battery SOC: {soc}%")
                else:
                    print(f"[{timestamp}] Failed to get battery SOC")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\nStopping monitor...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)

if __name__ == "__main__":
    monitor = EG4CloudSimple()
    
    print("EG4 Cloud Monitor - Battery SOC")
    print("="*50)
    
    # Test single fetch
    soc = monitor.get_battery_soc()
    
    if soc is not None:
        print(f"\n✓ Successfully retrieved battery SOC: {soc}%")
        
        # Start continuous monitoring
        monitor.run_continuous(interval=30)
    else:
        print("\n✗ Failed to retrieve battery SOC")
        print("\nPossible issues:")
        print("1. Check username/password in .env file")
        print("2. The page might require JavaScript - try: python3 eg4_cloud_selenium.py")
        print("3. Check eg4_monitor_page.html to see the actual page content")