#!/usr/bin/env python3
"""
EG4 Web Monitor - With file editor
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

# Configuration files directory
CONFIG_DIR = Path(__file__).parent
ALLOWED_FILES = ['.env', 'config.yaml', 'config.json', 'settings.json', 'alert_config.json']
ALLOWED_EXTENSIONS = ['.env', '.yaml', '.yml', '.json', '.txt', '.conf', '.ini']

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
        'current_violations': []
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
            if i % 5 == 0:
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
                        if (!text || text === '--' || text === '') return '';
                        return text.trim();
                    };
                    
                    // Battery Status
                    const battPower = cleanText(document.querySelector('.batteryPowerText')?.textContent);
                    const battSoc = cleanText(document.querySelector('.socText')?.textContent);
                    const battVoltage = cleanText(document.querySelector('.vbatText')?.textContent);
                    
                    data.battery = {
                        power: battPower ? battPower + ' W' : '--',
                        soc: battSoc ? battSoc + '%' : '--',
                        voltage: battVoltage ? battVoltage + ' V' : '--',
                        current: '--'
                    };
                    
                    // PV Status
                    const pv1 = parseInt(cleanText(document.querySelector('.pv1PowerText')?.textContent)) || 0;
                    const pv2 = parseInt(cleanText(document.querySelector('.pv2PowerText')?.textContent)) || 0;
                    const pv3 = parseInt(cleanText(document.querySelector('.pv3PowerText')?.textContent)) || 0;
                    const pvTotal = pv1 + pv2 + pv3;
                    
                    data.pv = {
                        pv1_power: pv1 + ' W',
                        pv2_power: pv2 + ' W',
                        total_power: pvTotal + ' W'
                    };
                    
                    // Grid Status
                    const gridPower = cleanText(document.querySelector('.gridPowerText')?.textContent);
                    const gridVoltage = cleanText(document.querySelector('.vacText')?.textContent);
                    const gridFreq = cleanText(document.querySelector('.facText')?.textContent);
                    
                    data.grid = {
                        power: gridPower ? gridPower + ' W' : '--',
                        voltage: gridVoltage ? gridVoltage + ' V' : '--',
                        frequency: gridFreq ? gridFreq + ' Hz' : '--'
                    };
                    
                    // Load/Consumption
                    const loadPower = cleanText(document.querySelector('.consumptionPowerText')?.textContent);
                    
                    data.load = {
                        power: loadPower ? loadPower + ' W' : '--',
                        percentage: '--'
                    };
                    
                    // Daily statistics
                    const solarYield = cleanText(document.querySelector('#todayYieldingText')?.textContent);
                    const consumption = cleanText(document.querySelector('#todayUsageText')?.textContent);
                    const gridImport = cleanText(document.querySelector('#todayImportText')?.textContent);
                    const gridExport = cleanText(document.querySelector('#todayExportText')?.textContent);
                    
                    data.daily = {
                        solar_yield: solarYield ? solarYield + ' kWh' : '--',
                        consumption: consumption ? consumption + ' kWh' : '--',
                        grid_import: gridImport ? gridImport + ' kWh' : '--',
                        grid_export: gridExport ? gridExport + ' kWh' : '--'
                    };
                    
                    // System Info
                    data.system = {
                        status: cleanText(document.querySelector('#infoListLabel')?.textContent) || 'Normal',
                        temperature: cleanText(document.querySelector('.tempText')?.textContent) || '--'
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

class SRPMonitor:
    def __init__(self, username=None, password=None):
        self.username = (username or os.getenv('SRP_USERNAME', '')).strip().strip("'\"")
        self.password = (password or os.getenv('SRP_PASSWORD', '')).strip().strip("'\"")
        self.base_url = 'https://myaccount.srpnet.com'
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def start(self):
        """Start the browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        
    async def login(self):
        """Login to SRP account"""
        try:
            print(f"Attempting SRP login with username: {self.username}")
            app.logger.info(f"SRP login attempt for user: {self.username}")
            
            # Go directly to the login page
            await self.page.goto('https://myaccount.srpnet.com/power', wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Check if we're already logged in
            if 'Dashboard' in self.page.url and 'login' not in self.page.url.lower():
                print("Already logged in to SRP")
                app.logger.info("SRP already logged in")
                return True
            
            # Look for the login form
            try:
                # Try desktop username field first
                username_field = await self.page.wait_for_selector('input[name="username"], input#username_desktop', timeout=10000)
                await username_field.fill(self.username)
                print("Filled username")
                app.logger.info("SRP username filled")
                
                # Fill password
                password_field = await self.page.query_selector('input[name="password"], input#password_desktop')
                if password_field:
                    await password_field.fill(self.password)
                    print("Filled password")
                    app.logger.info("SRP password filled")
                    
                    # Submit the form by pressing Enter (more reliable than clicking button)
                    await password_field.press('Enter')
                    print("Pressed Enter to submit")
                    app.logger.info("SRP form submitted with Enter")
                    
                    # Wait for navigation
                    await asyncio.sleep(5)
                    
                    # Navigate to the usage page where peak demand is shown
                    await self.page.goto(f"{self.base_url}/power/myaccount/usage", wait_until='networkidle')
                    await asyncio.sleep(3)
                    
                    # Check if login successful
                    current_url = self.page.url
                    if 'myaccount' in current_url.lower() and 'login' not in current_url.lower():
                        print("SRP login successful!")
                        app.logger.info("SRP login successful")
                        return True
                    else:
                        print(f"SRP login failed - ended up at: {current_url}")
                        app.logger.error(f"SRP login failed - URL: {current_url}")
                        return False
                        
            except Exception as e:
                print(f"Login form error: {e}")
                app.logger.error(f"SRP login form error: {e}")
                return False
                
        except Exception as e:
            print(f"SRP login error: {e}")
            app.logger.error(f"SRP login error: {e}")
            return False
    
    async def get_peak_demand(self):
        """Get peak demand data from SRP usage page"""
        try:
            # Make sure we're on the usage page
            current_url = self.page.url
            if 'usage' not in current_url:
                await self.page.goto(f"{self.base_url}/power/myaccount/usage", wait_until='networkidle')
                await asyncio.sleep(2)
            
            # Extract peak demand value from the specific element
            demand_data = await self.page.evaluate("""
                () => {
                    // Look for the specific srp-red-text element with kW value
                    const srpRedText = document.querySelector('.srp-red-text strong');
                    let demandValue = '--';
                    
                    if (srpRedText) {
                        demandValue = srpRedText.textContent.trim();
                    } else {
                        // Fallback: look for any element with srp-red-text class
                        const redTexts = document.querySelectorAll('.srp-red-text');
                        for (const elem of redTexts) {
                            const text = elem.textContent || '';
                            if (text.includes('kW')) {
                                demandValue = text.trim();
                                break;
                            }
                        }
                    }
                    
                    // Get billing cycle info if available
                    let cycleInfo = '';
                    const billingTexts = document.querySelectorAll('*');
                    for (const elem of billingTexts) {
                        const text = elem.textContent || '';
                        if (text.includes('Billing cycle') || text.includes('billing period')) {
                            cycleInfo = text.trim();
                            break;
                        }
                    }
                    
                    // Also collect all kW values on the page for debugging
                    const bodyText = document.body.textContent || '';
                    const kwRegex = /(\\d+\\.?\\d*)\\s*kW/gi;
                    const allKwValues = bodyText.match(kwRegex) || [];
                    
                    return {
                        demand: demandValue,
                        type: 'PEAK DEMAND',
                        cycleInfo: cycleInfo,
                        timestamp: new Date().toISOString(),
                        allKwValues: allKwValues.slice(0, 10),  // For debugging
                        url: window.location.href  // For debugging
                    };
                }
            """)
            
            if demand_data:
                print(f"SRP demand extracted: {demand_data['demand']} from {demand_data['url']}")
                if demand_data.get('allKwValues'):
                    print(f"All kW values found on page: {demand_data['allKwValues']}")
                app.logger.info(f"SRP demand: {demand_data['demand']}")
            
            return demand_data
            
        except Exception as e:
            print(f"Error getting peak demand: {e}")
            app.logger.error(f"Error getting peak demand: {e}")
            return {'error': str(e), 'demand': '--', 'type': 'ERROR'}
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

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
    return render_template('index_solar_style.html')

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
            'credentials_verified': credentials_verified,
            'srp_username': os.getenv('SRP_USERNAME', '').strip().strip("'\"")
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
                # Read existing content
                env_content = {}
                if env_path.exists():
                    with open(env_path, 'r') as f:
                        for line in f:
                            if '=' in line and not line.strip().startswith('#'):
                                key, value = line.strip().split('=', 1)
                                env_content[key] = value
                
                # Update values
                env_content['EG4_MONITOR_USERNAME'] = username
                env_content['EG4_MONITOR_PASSWORD'] = password
                
                # Write back without quotes
                with open(env_path, 'w') as f:
                    for key, value in env_content.items():
                        f.write(f"{key}={value}\n")
                
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
        
        # Update SRP credentials if provided
        if 'srp_username' in data and 'srp_password' in data:
            srp_username = data['srp_username'].strip()
            srp_password = data['srp_password'].strip()
            
            # Save to environment and .env file
            os.environ['SRP_USERNAME'] = srp_username
            os.environ['SRP_PASSWORD'] = srp_password
            
            # Update .env file without quotes
            env_path = Path('.env')
            # Read existing content
            env_content = {}
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            env_content[key] = value
            
            # Update SRP values
            env_content['SRP_USERNAME'] = srp_username
            env_content['SRP_PASSWORD'] = srp_password
            
            # Write back without quotes
            with open(env_path, 'w') as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            return jsonify({'status': 'success', 'message': 'SRP credentials saved'})
        
        return jsonify({'status': 'success'})

@app.route('/api/monitor/data', methods=['GET'])
def get_monitor_data():
    """Get current monitor data"""
    return jsonify(monitor_data)

@app.route('/api/srp/demand', methods=['GET'])
def get_srp_demand():
    """Get SRP peak demand data"""
    async def fetch_srp_data():
        srp = SRPMonitor()
        try:
            await srp.start()
            if await srp.login():
                demand_data = await srp.get_peak_demand()
                return demand_data
            else:
                return {'error': 'Failed to login to SRP'}
        except Exception as e:
            return {'error': str(e)}
        finally:
            await srp.close()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(fetch_srp_data())
    
    return jsonify(result)

@app.route('/api/files', methods=['GET'])
def list_files():
    """List available configuration files"""
    files = []
    
    # List files in current directory
    for file in CONFIG_DIR.iterdir():
        if file.is_file() and (file.name in ALLOWED_FILES or file.suffix in ALLOWED_EXTENSIONS):
            files.append({
                'name': file.name,
                'size': file.stat().st_size,
                'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
    
    # Check for config subdirectory
    config_subdir = CONFIG_DIR / 'config'
    if config_subdir.exists():
        for file in config_subdir.iterdir():
            if file.is_file() and (file.name in ALLOWED_FILES or file.suffix in ALLOWED_EXTENSIONS):
                files.append({
                    'name': f'config/{file.name}',
                    'size': file.stat().st_size,
                    'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
    
    return jsonify(files)

@app.route('/api/files/<path:filename>', methods=['GET', 'PUT'])
def handle_file(filename):
    """Get or update file contents"""
    # Security check
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid filename'}), 400
    
    file_path = CONFIG_DIR / filename
    
    if request.method == 'GET':
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        try:
            content = file_path.read_text()
            return jsonify({
                'content': content,
                'name': filename
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'PUT':
        data = request.json
        content = data.get('content', '')
        
        try:
            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path.write_text(content)
            
            # If it's .env file, reload environment
            if filename == '.env':
                load_dotenv()
            
            return jsonify({'status': 'success', 'message': f'File {filename} saved successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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