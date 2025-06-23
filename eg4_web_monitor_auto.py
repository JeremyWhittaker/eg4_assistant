#!/usr/bin/env python3
"""
EG4 Web Monitor - Auto-monitoring version
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, time
import os
from dotenv import load_dotenv, set_key
import json
import threading
import time as time_module
from collections import deque
import secrets
from pathlib import Path

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
monitor_thread = None
monitor_running = False
monitor_data = {}
credentials_verified = False
alert_config = {
    'battery_soc': {
        'enabled': False,
        'check_time': '06:00',
        'min_soc': 80,
        'last_check': None
    },
    'peak_demand': {
        'enabled': False,
        'start_time': '16:00',
        'end_time': '21:00',
        'max_load': 5000,
        'duration_minutes': 5,
        'current_violations': []  # Changed from deque to list for JSON serialization
    },
    'cloud_connectivity': {
        'enabled': False,
        'last_success': None,
        'consecutive_failures': 0
    }
}

class EG4WebMonitor:
    def __init__(self, username=None, password=None):
        # Strip quotes from credentials
        self.username = (username or os.getenv('EG4_MONITOR_USERNAME', '')).strip().strip("'\"")
        self.password = (password or os.getenv('EG4_MONITOR_PASSWORD', '')).strip().strip("'\"")
        self.base_url = 'https://monitor.eg4electronics.com'
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def start(self):
        """Start the browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        
    async def login(self):
        """Login to EG4 cloud monitor"""
        try:
            print(f"Attempting login with username: {self.username}")
            await self.page.goto(f"{self.base_url}/WManage/web/login", wait_until='networkidle')
            await self.page.wait_for_selector('input[name="account"]', timeout=10000)
            
            await self.page.fill('input[name="account"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            current_url = self.page.url
            login_success = 'login' not in current_url
            
            if login_success:
                print("Login successful!")
            else:
                print("Login failed - still on login page")
            
            return login_success
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def verify_credentials(self):
        """Quick verification of credentials"""
        try:
            await self.start()
            success = await self.login()
            await self.close()
            return success
        except Exception as e:
            print(f"Credential verification error: {e}")
            if self.browser:
                await self.close()
            return False
    
    async def wait_for_data(self):
        """Wait for real data to load on the page"""
        print("Waiting for data to load...")
        for i in range(30):
            await asyncio.sleep(1)
            soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
            if i % 5 == 0:  # Only log every 5 seconds
                print(f"Checking SOC ({i+1}/30): {soc}")
            if soc and soc != '--':
                print(f"Data loaded! SOC: {soc}")
                return True
        print("Data did not load after 30 seconds")
        return False
    
    async def navigate_to_monitor(self):
        """Navigate to the monitor page and wait for data"""
        print("Navigating to monitor page...")
        await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
        
        await asyncio.sleep(2)
        
        # Try to click on the first inverter if there's a selection screen
        try:
            inverter_selector = await self.page.query_selector('.inverter-item, [class*="inverter-card"]')
            if inverter_selector:
                print("Found inverter selector, clicking...")
                await inverter_selector.click()
                await asyncio.sleep(2)
        except:
            pass
        
        if not await self.wait_for_data():
            print("Warning: Data did not load after 30 seconds")
            return False
        return True
    
    async def extract_all_data(self):
        """Extract comprehensive data from the page"""
        try:
            stats = await self.page.evaluate("""
                () => {
                    let data = {};
                    
                    // Helper function to clean text
                    const cleanText = (text) => {
                        if (!text || text === '--' || text === '') return '--';
                        return text.trim();
                    };
                    
                    // Battery Status
                    data.battery = {
                        power: cleanText(document.querySelector('.batteryPowerText')?.textContent || 
                                       document.querySelector('[class*="battery-power"]')?.textContent),
                        soc: cleanText(document.querySelector('.socText')?.textContent ||
                                     document.querySelector('[class*="soc-text"]')?.textContent),
                        voltage: cleanText(document.querySelector('.vbatText')?.textContent ||
                                         document.querySelector('[class*="vbat"]')?.textContent),
                        current: cleanText(document.querySelector('.batteryCurrentText')?.textContent ||
                                         document.querySelector('[class*="battery-current"]')?.textContent)
                    };
                    
                    // PV Status
                    data.pv = {
                        pv1_power: cleanText(document.querySelector('.pv1PowerText')?.textContent ||
                                           document.querySelector('[class*="pv1-power"]')?.textContent),
                        pv2_power: cleanText(document.querySelector('.pv2PowerText')?.textContent ||
                                           document.querySelector('[class*="pv2-power"]')?.textContent),
                        total_power: cleanText(document.querySelector('.pvPowerText')?.textContent ||
                                             document.querySelector('[class*="pv-power"]')?.textContent)
                    };
                    
                    // Grid Status
                    data.grid = {
                        power: cleanText(document.querySelector('.gridPowerText')?.textContent ||
                                       document.querySelector('[class*="grid-power"]')?.textContent),
                        voltage: cleanText(document.querySelector('.vacText')?.textContent ||
                                         document.querySelector('[class*="vac"]')?.textContent),
                        frequency: cleanText(document.querySelector('.facText')?.textContent ||
                                           document.querySelector('[class*="fac"]')?.textContent)
                    };
                    
                    // Load/Consumption
                    data.load = {
                        power: cleanText(document.querySelector('.consumptionPowerText')?.textContent ||
                                       document.querySelector('[class*="consumption-power"]')?.textContent ||
                                       document.querySelector('[class*="load-power"]')?.textContent),
                        percentage: cleanText(document.querySelector('.loadPercentText')?.textContent ||
                                            document.querySelector('[class*="load-percent"]')?.textContent)
                    };
                    
                    // Daily statistics
                    data.daily = {
                        solar_yield: cleanText(document.querySelector('#todayYieldingText')?.textContent ||
                                             document.querySelector('[class*="today-yield"]')?.textContent ||
                                             document.querySelector('[class*="daily-solar"]')?.textContent),
                        consumption: cleanText(document.querySelector('#todayUsageText')?.textContent ||
                                             document.querySelector('[class*="today-usage"]')?.textContent ||
                                             document.querySelector('[class*="daily-consumption"]')?.textContent)
                    };
                    
                    // System Info
                    data.system = {
                        status: cleanText(document.querySelector('#infoListLabel')?.textContent ||
                                        document.querySelector('[class*="status"]')?.textContent ||
                                        'Online'),
                        temperature: cleanText(document.querySelector('.tempText')?.textContent ||
                                             document.querySelector('[class*="temp"]')?.textContent)
                    };
                    
                    return data;
                }
            """)
            
            return stats
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            return None
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def verify_credentials_async(username, password):
    """Verify credentials asynchronously"""
    monitor = EG4WebMonitor(username, password)
    return await monitor.verify_credentials()

def check_alerts(data):
    """Check all configured alerts and send notifications"""
    alerts = []
    current_time = datetime.now()
    
    # Battery SOC Alert
    if alert_config['battery_soc']['enabled']:
        check_time_str = alert_config['battery_soc']['check_time']
        check_hour, check_minute = map(int, check_time_str.split(':'))
        
        # Check if it's time and we haven't checked today
        if (current_time.time().hour == check_hour and 
            current_time.time().minute == check_minute and
            alert_config['battery_soc']['last_check'] != current_time.date()):
            
            alert_config['battery_soc']['last_check'] = current_time.date()
            
            if data and 'battery' in data:
                soc_str = data['battery']['soc']
                if soc_str != '--':
                    soc = int(soc_str.replace('%', ''))
                    min_soc = alert_config['battery_soc']['min_soc']
                    if soc < min_soc:
                        alert = {
                            'type': 'battery_soc',
                            'message': f'Battery SOC Alert: {soc}% is below minimum {min_soc}% at {check_time_str}',
                            'severity': 'warning',
                            'timestamp': current_time.isoformat()
                        }
                        alerts.append(alert)
                        socketio.emit('alert', alert)
    
    # Peak Demand Alert
    if alert_config['peak_demand']['enabled'] and data and 'load' in data:
        start_time_str = alert_config['peak_demand']['start_time']
        end_time_str = alert_config['peak_demand']['end_time']
        start_hour, start_minute = map(int, start_time_str.split(':'))
        end_hour, end_minute = map(int, end_time_str.split(':'))
        
        current_minutes = current_time.hour * 60 + current_time.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        
        # Check if we're in the monitoring window
        if start_minutes <= current_minutes <= end_minutes:
            load_str = data['load']['power']
            if load_str != '--':
                try:
                    load = int(load_str.replace('W', '').replace(',', '').strip())
                    max_load = alert_config['peak_demand']['max_load']
                    
                    # Track violations (keep only last 60)
                    violations = alert_config['peak_demand']['current_violations']
                    if load > max_load:
                        violations.append(current_time.isoformat())
                        # Keep only last 60 entries
                        if len(violations) > 60:
                            violations.pop(0)
                    
                    # Check if we have enough consecutive violations
                    duration_minutes = alert_config['peak_demand']['duration_minutes']
                    if len(violations) >= duration_minutes:
                        # Check if violations are consecutive
                        recent_violations = [v for v in violations 
                                           if (current_time - datetime.fromisoformat(v)).seconds < duration_minutes * 60]
                        if len(recent_violations) >= duration_minutes:
                            alert = {
                                'type': 'peak_demand',
                                'message': f'Peak Demand Alert: Load {load}W exceeded {max_load}W for {duration_minutes} minutes',
                                'severity': 'critical',
                                'timestamp': current_time.isoformat()
                            }
                            alerts.append(alert)
                            socketio.emit('alert', alert)
                            # Clear violations to prevent repeated alerts
                            violations.clear()
                except:
                    pass
    
    return alerts

async def monitor_loop():
    """Background monitoring loop"""
    global monitor_data, monitor_running, credentials_verified
    
    if not credentials_verified:
        print("Credentials not verified, stopping monitor")
        monitor_data = {'error': 'Credentials not verified'}
        return
    
    monitor = EG4WebMonitor()
    await monitor.start()
    
    try:
        if not await monitor.login():
            print("Login failed")
            monitor_data = {'error': 'Login failed - check credentials'}
            credentials_verified = False
            return
        
        if not await monitor.navigate_to_monitor():
            print("Failed to load monitor data")
            monitor_data = {'error': 'Failed to load monitor data'}
            return
        
        while monitor_running:
            data = await monitor.extract_all_data()
            if data:
                data['timestamp'] = datetime.now().isoformat()
                monitor_data = data
                
                # Check alerts
                check_alerts(data)
                
                # Emit data to connected clients
                socketio.emit('monitor_update', data)
                print(f"Data update sent: SOC={data['battery']['soc']}")
            
            # Wait before next update
            for i in range(30):
                if not monitor_running:
                    break
                await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Monitor error: {e}")
        monitor_data = {'error': str(e)}
    finally:
        await monitor.close()

def run_monitor():
    """Run the monitor in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(monitor_loop())

def start_monitoring_if_needed():
    """Start monitoring if credentials are verified"""
    global monitor_thread, monitor_running
    
    if credentials_verified and not monitor_running:
        monitor_running = True
        monitor_thread = threading.Thread(target=run_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        print("Auto-started monitoring")

@app.route('/')
def index():
    """Main page with tabs"""
    return render_template('index_auto.html')

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update configuration"""
    global credentials_verified
    
    if request.method == 'GET':
        # Clean up alert config for JSON serialization
        config_copy = {
            'username': os.getenv('EG4_MONITOR_USERNAME', '').strip().strip("'\""),
            'alerts': {
                'battery_soc': {
                    'enabled': alert_config['battery_soc']['enabled'],
                    'check_time': alert_config['battery_soc']['check_time'],
                    'min_soc': alert_config['battery_soc']['min_soc']
                },
                'peak_demand': {
                    'enabled': alert_config['peak_demand']['enabled'],
                    'start_time': alert_config['peak_demand']['start_time'],
                    'end_time': alert_config['peak_demand']['end_time'],
                    'max_load': alert_config['peak_demand']['max_load'],
                    'duration_minutes': alert_config['peak_demand']['duration_minutes']
                },
                'cloud_connectivity': {
                    'enabled': alert_config['cloud_connectivity']['enabled']
                }
            },
            'credentials_verified': credentials_verified
        }
        return jsonify(config_copy)
    
    elif request.method == 'POST':
        data = request.json
        
        # Update credentials if provided
        if 'username' in data and 'password' in data:
            username = data['username'].strip()
            password = data['password'].strip()
            
            # Verify credentials first
            print(f"Verifying credentials for user: {username}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            verified = loop.run_until_complete(verify_credentials_async(username, password))
            
            if verified or data.get('force_save', False):
                # Save to environment and .env file
                os.environ['EG4_MONITOR_USERNAME'] = username
                os.environ['EG4_MONITOR_PASSWORD'] = password
                
                # Create or update .env file (without quotes)
                env_path = Path('.env')
                set_key(env_path, 'EG4_MONITOR_USERNAME', username)
                set_key(env_path, 'EG4_MONITOR_PASSWORD', password)
                
                if verified:
                    credentials_verified = True
                    print("Credentials verified and saved!")
                    # Auto-start monitoring
                    start_monitoring_if_needed()
                    return jsonify({
                        'status': 'success',
                        'message': 'Credentials verified and saved successfully'
                    })
                else:
                    return jsonify({
                        'status': 'saved',
                        'message': 'Credentials saved but could not be verified'
                    })
            else:
                return jsonify({
                    'status': 'invalid',
                    'message': 'Invalid credentials - please check username and password',
                    'verified': False
                })
        
        # Update alerts if provided
        if 'alerts' in data:
            for key in data['alerts']:
                if key in alert_config:
                    alert_config[key].update(data['alerts'][key])
        
        return jsonify({'status': 'success'})

@app.route('/api/monitor/data', methods=['GET'])
def get_monitor_data():
    """Get current monitor data"""
    return jsonify(monitor_data)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to EG4 Web Monitor'})
    print("Client connected")
    # Send current data if available
    if monitor_data and 'error' not in monitor_data:
        emit('monitor_update', monitor_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    # Check if credentials exist
    username = os.getenv('EG4_MONITOR_USERNAME', '').strip().strip("'\"")
    password = os.getenv('EG4_MONITOR_PASSWORD', '').strip().strip("'\"")
    
    if username and password:
        # Verify existing credentials
        print("Verifying existing credentials...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        credentials_verified = loop.run_until_complete(verify_credentials_async(username, password))
        
        if credentials_verified:
            print("Existing credentials verified!")
            # Auto-start monitoring
            monitor_running = True
            monitor_thread = threading.Thread(target=run_monitor)
            monitor_thread.daemon = True
            monitor_thread.start()
        else:
            print("Existing credentials could not be verified")
    
    socketio.run(app, host='0.0.0.0', port=8282, debug=True)