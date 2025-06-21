#!/usr/bin/env python3
"""
EG4 Cloud Monitor using Selenium - Handles JavaScript-rendered pages
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EG4CloudSelenium:
    def __init__(self, headless=True):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        
        # Setup Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except:
            print("Chrome driver not found, trying Firefox...")
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            firefox_options = FirefoxOptions()
            if headless:
                firefox_options.add_argument("--headless")
            self.driver = webdriver.Firefox(options=firefox_options)
        
        self.wait = WebDriverWait(self.driver, 20)
        self.logged_in = False
    
    def login(self):
        """Login to EG4 cloud monitor"""
        try:
            print("Opening login page...")
            self.driver.get(f"{self.base_url}/WManage/web/login")
            time.sleep(2)
            
            # Find and fill username field
            username_selectors = [
                "input[name='username']",
                "input[name='user']",
                "input[name='email']",
                "input[type='text']",
                "#username",
                "#user"
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not username_field:
                print("Could not find username field")
                return False
            
            username_field.clear()
            username_field.send_keys(self.username)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Find and click login button
            login_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Login')",
                "button:contains('Sign In')",
                ".login-button",
                "#loginBtn"
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    if ':contains' in selector:
                        # Use XPath for text content
                        xpath = f"//button[contains(text(), '{selector.split('contains')[1].strip('()\\'\"')}')]"
                        login_button = self.driver.find_element(By.XPATH, xpath)
                    else:
                        login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if login_button:
                login_button.click()
            else:
                # Try submitting the form
                password_field.submit()
            
            time.sleep(3)
            
            # Check if login was successful
            if "login" not in self.driver.current_url.lower():
                print("Login successful!")
                self.logged_in = True
                return True
            else:
                print("Login may have failed")
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
            # Navigate to monitor page
            monitor_url = f"{self.base_url}/WManage/web/monitor/inverter"
            print(f"Opening monitor page: {monitor_url}")
            self.driver.get(monitor_url)
            
            # Wait for data to load
            time.sleep(3)
            
            data = {}
            
            # Get battery SOC
            try:
                soc_element = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".socText.monitorDataText"))
                )
                soc_text = soc_element.text.strip()
                if soc_text.isdigit():
                    data['battery_soc'] = int(soc_text)
                    print(f"Found Battery SOC: {data['battery_soc']}%")
            except:
                # Try alternate selector
                try:
                    soc_element = self.driver.find_element(By.CSS_SELECTOR, ".socHolder")
                    soc_text = soc_element.text
                    import re
                    match = re.search(r'(\d+)%', soc_text)
                    if match:
                        data['battery_soc'] = int(match.group(1))
                        print(f"Found Battery SOC: {data['battery_soc']}%")
                except:
                    print("Could not find battery SOC")
            
            # Look for other data elements
            data_selectors = {
                'battery_voltage': ['.batteryVoltage', '.battery-voltage', '[data-field="battery_voltage"]'],
                'battery_power': ['.batteryPower', '.battery-power', '[data-field="battery_power"]'],
                'grid_power': ['.gridPower', '.grid-power', '[data-field="grid_power"]'],
                'pv_power': ['.pvPower', '.pv-power', '.solarPower', '[data-field="pv_power"]'],
                'load_power': ['.loadPower', '.load-power', '[data-field="load_power"]']
            }
            
            for field, selectors in data_selectors.items():
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        text = element.text.strip()
                        # Extract number from text
                        import re
                        match = re.search(r'-?\d+\.?\d*', text.replace(',', ''))
                        if match:
                            value = float(match.group()) if '.' in match.group() else int(match.group())
                            data[field] = value
                            print(f"Found {field}: {value}")
                            break
                    except:
                        continue
            
            # Try to extract data from JavaScript variables
            try:
                # Execute JavaScript to get any global data objects
                js_data = self.driver.execute_script("""
                    // Look for common data variable names
                    var data = {};
                    var possibleVars = ['inverterData', 'monitorData', 'liveData', 'realtimeData'];
                    
                    for (var i = 0; i < possibleVars.length; i++) {
                        if (window[possibleVars[i]]) {
                            data = window[possibleVars[i]];
                            break;
                        }
                    }
                    
                    return data;
                """)
                
                if js_data and isinstance(js_data, dict):
                    # Extract relevant values
                    key_mappings = {
                        'soc': 'battery_soc',
                        'batterySoc': 'battery_soc',
                        'batteryPower': 'battery_power',
                        'gridPower': 'grid_power',
                        'pvPower': 'pv_power',
                        'loadPower': 'load_power'
                    }
                    
                    for key, mapped_key in key_mappings.items():
                        if key in js_data:
                            data[mapped_key] = js_data[key]
                            print(f"Found {mapped_key} from JS: {js_data[key]}")
                            
            except Exception as e:
                print(f"Could not extract JS data: {e}")
            
            return data
            
        except Exception as e:
            print(f"Error getting live data: {e}")
            self.logged_in = False
            return None
    
    def display_data(self, data):
        """Display the collected data"""
        print(f"\n{'='*60}")
        print(f"EG4 Cloud Monitor (Selenium) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if not data:
            print("No data available")
            return
        
        if 'battery_soc' in data:
            print(f"\nBattery SOC: {data['battery_soc']}%")
        
        if 'battery_voltage' in data:
            print(f"Battery Voltage: {data['battery_voltage']} V")
        
        if 'battery_power' in data:
            print(f"Battery Power: {data['battery_power']} W")
            
        if 'grid_power' in data:
            print(f"Grid Power: {data['grid_power']} W")
            
        if 'pv_power' in data:
            print(f"PV Power: {data['pv_power']} W")
            
        if 'load_power' in data:
            print(f"Load Power: {data['load_power']} W")
        
        print(f"\nTotal fields retrieved: {len(data)}")
    
    def close(self):
        """Close the browser"""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def run_continuous(self, interval=60):
        """Run continuous monitoring"""
        print("EG4 Cloud Monitor (Selenium)")
        print("Monitoring live statistics from monitor.eg4electronics.com")
        print(f"Update interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                try:
                    data = self.get_live_data()
                    self.display_data(data)
                    time.sleep(interval)
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        finally:
            self.close()

if __name__ == "__main__":
    # Test with visible browser first
    print("Testing EG4 cloud monitor with Selenium...")
    print("Note: This requires Chrome or Firefox with appropriate driver installed")
    print("Install with: sudo apt-get install chromium-chromedriver")
    print("Or: pip install geckodriver-autoinstaller\n")
    
    monitor = EG4CloudSelenium(headless=False)  # Set to True for headless mode
    
    try:
        data = monitor.get_live_data()
        
        if data:
            monitor.display_data(data)
            print("\n✓ Successfully retrieved data from EG4 cloud!")
            
            # Ask if user wants continuous monitoring
            response = input("\nStart continuous monitoring? (y/n): ")
            if response.lower() == 'y':
                monitor.run_continuous(interval=30)
        else:
            print("\n✗ Failed to retrieve data")
            print("Please check the browser window for any issues")
    finally:
        monitor.close()