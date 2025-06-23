#!/usr/bin/env python3
"""
EG4 Web Monitor v2 - Web interface with credential verification
"""

from flask import Flask, render_template, request, jsonify, session
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
        'current_violations': deque(maxlen=60)
    },
    'cloud_connectivity': {
        'enabled': False,
        'last_success': None,
        'consecutive_failures': 0
    }
}

class EG4WebMonitor:
    def __init__(self, username=None, password=None):
        self.username = username or os.getenv('EG4_MONITOR_USERNAME')
        self.password = password or os.getenv('EG4_MONITOR_PASSWORD')
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
            await asyncio.sleep(2)  # Give login time to process
            
            # Check if we're still on login page
            current_url = self.page.url
            login_success = 'login' not in current_url
            
            if login_success:
                print("Login successful!")
            else:
                print("Login failed - still on login page")
                # Try to get error message
                error_msg = await self.page.evaluate("""
                    () => {
                        const errorEl = document.querySelector('.el-message__content') || 
                                       document.querySelector('.error-message') ||
                                       document.querySelector('[class*="error"]');
                        return errorEl ? errorEl.textContent : null;
                    }
                """)
                if error_msg:
                    print(f"Login error: {error_msg}")
            
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
            await self.close()
            return False
    
    async def wait_for_data(self):
        """Wait for real data to load on the page"""
        print("Waiting for data to load...")
        for i in range(30):
            await asyncio.sleep(1)
            soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
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
        
        # Check if we need to select an inverter
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
                    
                    // Daily statistics - look for multiple possible selectors
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
                    
                    // Add debug info
                    data.debug = {
                        url: window.location.href,
                        title: document.title,
                        hasData: data.battery.soc !== '--'
                    };
                    
                    return data;
                }
            """)
            
            print(f"Extracted data: {json.dumps(stats, indent=2)}")
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
            monitor_data = {'error': 'Login failed'}
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
                print(f"Emitted update at {data['timestamp']}")
            
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

@app.route('/')
def index():
    """Main page with tabs"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update configuration"""
    global credentials_verified
    
    if request.method == 'GET':
        return jsonify({
            'username': os.getenv('EG4_MONITOR_USERNAME', ''),
            'alerts': alert_config,
            'credentials_verified': credentials_verified
        })
    
    elif request.method == 'POST':
        data = request.json
        
        # Update credentials if provided
        if 'username' in data and 'password' in data:
            username = data['username']
            password = data['password']
            
            # Verify credentials first
            print(f"Verifying credentials for user: {username}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            verified = loop.run_until_complete(verify_credentials_async(username, password))
            
            if verified:
                # Save to environment and .env file
                os.environ['EG4_MONITOR_USERNAME'] = username
                os.environ['EG4_MONITOR_PASSWORD'] = password
                
                # Create or update .env file
                env_path = Path('.env')
                set_key(env_path, 'EG4_MONITOR_USERNAME', username)
                set_key(env_path, 'EG4_MONITOR_PASSWORD', password)
                
                credentials_verified = True
                print("Credentials verified and saved!")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Credentials verified and saved successfully'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid credentials - please check username and password'
                }), 400
        
        # Update alerts if provided
        if 'alerts' in data:
            alert_config.update(data['alerts'])
        
        return jsonify({'status': 'success'})

@app.route('/api/test-credentials', methods=['POST'])
def test_credentials():
    """Test credentials without saving"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password required'}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    verified = loop.run_until_complete(verify_credentials_async(username, password))
    
    if verified:
        return jsonify({'status': 'success', 'message': 'Credentials are valid'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 400

@app.route('/api/monitor/start', methods=['POST'])
def start_monitor():
    """Start the monitoring thread"""
    global monitor_thread, monitor_running
    
    if not credentials_verified:
        return jsonify({
            'status': 'error',
            'message': 'Please verify credentials first'
        }), 400
    
    if not monitor_running:
        monitor_running = True
        monitor_thread = threading.Thread(target=run_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        return jsonify({'status': 'started'})
    
    return jsonify({'status': 'already_running'})

@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitor():
    """Stop the monitoring thread"""
    global monitor_running
    
    monitor_running = False
    return jsonify({'status': 'stopped'})

@app.route('/api/monitor/data', methods=['GET'])
def get_monitor_data():
    """Get current monitor data"""
    return jsonify(monitor_data)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to EG4 Web Monitor'})
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    # Check if credentials exist
    if os.getenv('EG4_MONITOR_USERNAME') and os.getenv('EG4_MONITOR_PASSWORD'):
        credentials_verified = True
        print("Found existing credentials in environment")
    
    socketio.run(app, host='0.0.0.0', port=8282, debug=True)