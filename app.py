#!/usr/bin/env python3
"""
EG4-SRP Monitor - Simplified monitoring and alerting system
"""

from flask import Flask, render_template, jsonify, request, make_response
from flask_socketio import SocketIO, emit
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import subprocess
import threading
import time
import logging
import sys
import json
import pytz
from logging.handlers import RotatingFileHandler
from collections import deque

# Configure logging with rotation
LOG_FILE = '/tmp/eg4_srp_monitor.log'
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 3

# Create formatters
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set up root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Console handler (for Docker logs)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# Rotating file handler (for web interface)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=LOG_MAX_SIZE,
    backupCount=LOG_BACKUP_COUNT
)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# Get logger for this module
logger = logging.getLogger(__name__)

# In-memory log buffer for web interface (last 1000 lines)
log_buffer = deque(maxlen=1000)

class WebLogHandler(logging.Handler):
    """Custom handler to store logs in memory for web interface"""
    def emit(self, record):
        log_entry = self.format(record)
        log_buffer.append({
            'timestamp': record.created,
            'level': record.levelname,
            'message': log_entry
        })

# Add web handler to root logger
web_handler = WebLogHandler()
web_handler.setFormatter(log_formatter)
root_logger.addHandler(web_handler)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
monitor_data = {
    'eg4': {},
    'srp': {},
    'last_update': None
}

# Track manual refresh requests
manual_refresh_requested = False
last_manual_refresh = None

# Configuration file path
CONFIG_FILE = '/app/config/config.json'

# Default configuration
alert_config = {
    'email_enabled': False,
    'email_to': '',  # Comma-separated list of recipients
    'timezone': 'America/Phoenix',  # Default to Phoenix timezone
    'thresholds': {
        'battery_low': 20,
        'battery_check_hour': 6,  # Check battery at 6 AM
        'battery_check_minute': 0,
        'peak_demand': 5.0,
        'peak_demand_check_hour': 6,  # Check peak demand at 6 AM
        'peak_demand_check_minute': 0,
        'grid_import': 10000,
        'grid_import_start_hour': 14,  # 2 PM
        'grid_import_end_hour': 20     # 8 PM
    },
    'last_alerts': {
        'battery_checked_date': None,
        'peak_demand_checked_date': None,
        'grid_import_last_alert': None  # Timestamp of last grid import alert
    }
}

def load_config():
    """Load configuration from file if it exists"""
    global alert_config
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                # Merge with defaults to handle missing keys
                alert_config.update(saved_config)
                # Ensure all threshold keys exist
                for key, value in alert_config['thresholds'].items():
                    if key not in saved_config.get('thresholds', {}):
                        saved_config.setdefault('thresholds', {})[key] = value
                logger.info("Configuration loaded from file")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")

def save_config():
    """Save configuration to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(alert_config, f, indent=2)
        logger.info("Configuration saved to file")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")

class EG4Monitor:
    def __init__(self):
        self.username = os.getenv('EG4_USERNAME', '')
        self.password = os.getenv('EG4_PASSWORD', '')
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
        )
        self.page = await self.browser.new_page()
        
    async def login(self):
        try:
            logger.info("Attempting EG4 login")
            await self.page.goto('https://monitor.eg4electronics.com/WManage/web/login', wait_until='domcontentloaded')
            await self.page.fill('input[name="account"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            await asyncio.sleep(3)
            success = 'login' not in self.page.url
            if success:
                logger.info("EG4 login successful")
            else:
                logger.warning("EG4 login failed - still on login page")
            return success
        except Exception as e:
            logger.error(f"EG4 login error: {e}", exc_info=True)
            return False
    
    async def get_data(self):
        try:
            await self.page.goto('https://monitor.eg4electronics.com/WManage/web/monitor/inverter', wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Wait for data to load
            for _ in range(10):
                soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
                if soc and soc != '--':
                    break
                await asyncio.sleep(1)
            
            # Extract data
            data = await self.page.evaluate("""
                () => {
                    const cleanText = (text) => {
                        if (!text || text === '--') return '0';
                        return text.trim().replace(/[^0-9.-]/g, '');
                    };
                    
                    return {
                        battery: {
                            soc: parseInt(cleanText(document.querySelector('.socText')?.textContent)) || 0,
                            power: parseInt(cleanText(document.querySelector('.batteryPowerText')?.textContent)) || 0,
                            voltage: parseFloat(cleanText(document.querySelector('.vbatText')?.textContent)) || 0
                        },
                        pv: {
                            power: parseInt(cleanText(document.querySelector('.pvPowerText')?.textContent)) || 0
                        },
                        grid: {
                            power: parseInt(cleanText(document.querySelector('.gridPowerText')?.textContent)) || 0,
                            voltage: parseFloat(cleanText(document.querySelector('.vacText')?.textContent)) || 0
                        },
                        load: {
                            power: parseInt(cleanText(document.querySelector('.consumptionPowerText')?.textContent)) || 0
                        }
                    };
                }
            """)
            
            return data
            
        except Exception as e:
            logger.error(f"EG4 data extraction error: {e}")
            return None
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

class SRPMonitor:
    def __init__(self):
        self.username = os.getenv('SRP_USERNAME', '')
        self.password = os.getenv('SRP_PASSWORD', '')
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
        )
        self.page = await self.browser.new_page()
        
    async def login(self):
        try:
            await self.page.goto('https://myaccount.srpnet.com/power', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Check if already logged in
            if 'dashboard' in self.page.url:
                return True
                
            # Login
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            await asyncio.sleep(5)
            
            return 'dashboard' in self.page.url or 'myaccount' in self.page.url
            
        except Exception as e:
            logger.error(f"SRP login error: {e}")
            return False
    
    async def get_peak_demand(self):
        try:
            await self.page.goto('https://myaccount.srpnet.com/power/myaccount/usage', wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Extract peak demand
            demand_data = await self.page.evaluate("""
                () => {
                    const srpRedText = document.querySelector('.srp-red-text strong');
                    let demandValue = '0';
                    
                    if (srpRedText) {
                        demandValue = srpRedText.textContent.trim();
                    }
                    
                    return {
                        demand: parseFloat(demandValue) || 0,
                        timestamp: new Date().toISOString()
                    };
                }
            """)
            
            return demand_data
            
        except Exception as e:
            logger.error(f"SRP data error: {e}")
            return {'demand': 0}
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

def check_gmail_configured():
    """Check if gmail-send is configured"""
    try:
        # Try to run send-gmail with --check flag (or just check if command exists)
        result = subprocess.run(['send-gmail', '--help'], capture_output=True, text=True)
        if result.returncode == 0:
            # Check if credentials are configured by looking for the .env file
            gmail_env_path = os.path.expanduser('~/.gmail_send/.env')
            if os.path.exists(gmail_env_path):
                # Try to read current configuration
                try:
                    with open(gmail_env_path, 'r') as f:
                        content = f.read()
                        if 'GMAIL_ADDRESS=' in content:
                            # Extract email address
                            for line in content.split('\n'):
                                if line.startswith('GMAIL_ADDRESS='):
                                    email = line.split('=', 1)[1].strip()
                                    return True, f"Gmail configured with {email}"
                except:
                    pass
                return True, "Gmail configured"
            else:
                return False, "Gmail not configured. Configure through the web interface."
        else:
            return False, "send-gmail command not found. Install gmail-send package."
    except FileNotFoundError:
        return False, "send-gmail command not found. Install gmail-send package."
    except Exception as e:
        return False, f"Error checking gmail configuration: {str(e)}"

def configure_gmail(email_address, app_password):
    """Configure gmail-send with provided credentials"""
    try:
        # Create the gmail_send directory if it doesn't exist
        gmail_dir = os.path.expanduser('~/.gmail_send')
        os.makedirs(gmail_dir, exist_ok=True)
        
        # Write the .env file
        env_path = os.path.join(gmail_dir, '.env')
        with open(env_path, 'w') as f:
            f.write(f"GMAIL_ADDRESS={email_address}\n")
            f.write(f"GMAIL_APP_PASSWORD={app_password}\n")
        
        # Set proper permissions (read/write for owner only)
        os.chmod(env_path, 0o600)
        
        # Test the configuration by trying to send a test email
        test_cmd = [
            'send-gmail',
            '--to', email_address,
            '--subject', 'Gmail Configuration Test',
            '--body', 'Gmail has been successfully configured for EG4-SRP Monitor!'
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "Gmail configured successfully! Test email sent."
        else:
            # Configuration saved but test failed
            return False, f"Configuration saved but test failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Failed to configure Gmail: {str(e)}"

def send_alert_email(subject, message):
    """Send email alert using gmail-send integration"""
    if not alert_config['email_enabled'] or not alert_config['email_to']:
        return True, "Email alerts disabled or no recipients configured"
        
    try:
        # Format HTML body
        body = f"""
        <html>
        <body>
            <h2>EG4-SRP Monitor Alert</h2>
            <p>{message}</p>
            <hr>
            <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {alert_config.get('timezone', 'UTC')}</p>
            <p>Current Status:</p>
            <ul>
                <li>Battery SOC: {monitor_data['eg4'].get('battery', {}).get('soc', 'N/A')}%</li>
                <li>Battery Power: {monitor_data['eg4'].get('battery', {}).get('power', 'N/A')}W</li>
                <li>Battery Voltage: {monitor_data['eg4'].get('battery', {}).get('voltage', 'N/A')}V</li>
                <li>PV Power: {monitor_data['eg4'].get('pv', {}).get('power', 'N/A')}W</li>
                <li>Grid Power: {monitor_data['eg4'].get('grid', {}).get('power', 'N/A')}W</li>
                <li>Grid Voltage: {monitor_data['eg4'].get('grid', {}).get('voltage', 'N/A')}V</li>
                <li>Load Power: {monitor_data['eg4'].get('load', {}).get('power', 'N/A')}W</li>
                <li>SRP Peak Demand: {monitor_data['srp'].get('demand', 'N/A')}kW</li>
            </ul>
        </body>
        </html>
        """
        
        # Use gmail-send command
        cmd = [
            'send-gmail',
            '--to', alert_config['email_to'],
            '--subject', f"EG4-SRP Alert: {subject}",
            '--body', body,
            '--html'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Alert email sent: {subject}")
            return True, "Email sent successfully"
        else:
            error_msg = result.stderr.strip()
            if "not configured" in error_msg.lower() or "credentials" in error_msg.lower():
                logger.error("Gmail not configured. Run 'gmail-auth-setup' to configure.")
                return False, "Gmail not configured. Run 'gmail-auth-setup' on the host system to configure Gmail credentials."
            else:
                logger.error(f"Failed to send alert email: {error_msg}")
                return False, f"Failed to send email: {error_msg}"
        
    except FileNotFoundError:
        logger.error("send-gmail command not found")
        return False, "send-gmail command not found. Please install the gmail-send package."
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False, f"Error sending email: {str(e)}"

def check_thresholds():
    """Check if any thresholds are exceeded"""
    alerts = []
    # Get timezone-aware current time
    tz_name = alert_config.get('timezone', 'UTC')
    try:
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
    except:
        # Fallback to UTC if timezone is invalid
        now = datetime.now(pytz.UTC)
    
    today_str = now.strftime('%Y-%m-%d')
    
    if 'eg4' in monitor_data and monitor_data['eg4']:
        # Battery SOC alert - only check at specific time
        battery_check_hour = alert_config['thresholds'].get('battery_check_hour', 6)
        battery_check_minute = alert_config['thresholds'].get('battery_check_minute', 0)
        
        # Check if it's time to check battery and we haven't checked today
        if (now.hour == battery_check_hour and 
            now.minute == battery_check_minute and
            alert_config['last_alerts'].get('battery_checked_date') != today_str):
            
            soc = monitor_data['eg4'].get('battery', {}).get('soc', 0)
            if soc <= alert_config['thresholds']['battery_low']:
                alerts.append(('Low Battery', f'Battery SOC is {soc}% at {battery_check_hour:02d}:{battery_check_minute:02d} {tz_name} (threshold: {alert_config["thresholds"]["battery_low"]}%)'))
            
            # Mark as checked for today
            alert_config['last_alerts']['battery_checked_date'] = today_str
            save_config()
        
        # Grid import alert - only during configured hours
        grid_power = monitor_data['eg4'].get('grid', {}).get('power', 0)
        current_hour = now.hour
        start_hour = alert_config['thresholds']['grid_import_start_hour']
        end_hour = alert_config['thresholds']['grid_import_end_hour']
        
        # Check if current time is within alert window
        if start_hour <= current_hour < end_hour:
            if grid_power > alert_config['thresholds']['grid_import']:
                # Check if we haven't sent this alert recently (within 15 minutes)
                last_grid_alert = alert_config['last_alerts'].get('grid_import_last_alert')
                if last_grid_alert:
                    last_alert_time = datetime.fromisoformat(last_grid_alert)
                    if (now - last_alert_time).total_seconds() < 900:  # 15 minutes
                        return  # Skip alert if sent recently
                
                alerts.append(('High Grid Import', f'Grid import is {grid_power}W during peak hours ({start_hour}:00-{end_hour}:00 {tz_name}, threshold: {alert_config["thresholds"]["grid_import"]}W)'))
                alert_config['last_alerts']['grid_import_last_alert'] = now.isoformat()
                save_config()
    
    if 'srp' in monitor_data and monitor_data['srp']:
        # Peak demand alert - check at configured time
        peak_check_hour = alert_config['thresholds'].get('peak_demand_check_hour', 6)
        peak_check_minute = alert_config['thresholds'].get('peak_demand_check_minute', 0)
        
        if (now.hour == peak_check_hour and 
            now.minute == peak_check_minute and
            alert_config['last_alerts'].get('peak_demand_checked_date') != today_str):
            
            demand = monitor_data['srp'].get('demand', 0)
            if demand > alert_config['thresholds']['peak_demand']:
                alerts.append(('High Peak Demand', f'Peak demand is {demand}kW at {peak_check_hour:02d}:{peak_check_minute:02d} {tz_name} (threshold: {alert_config["thresholds"]["peak_demand"]}kW)'))
            
            # Mark as checked for today
            alert_config['last_alerts']['peak_demand_checked_date'] = today_str
            save_config()
    
    # Send alerts
    for subject, message in alerts:
        success, _ = send_alert_email(subject, message)
        socketio.emit('alert', {'subject': subject, 'message': message, 'timestamp': datetime.now().isoformat()})

async def monitor_loop():
    """Main monitoring loop with automatic recovery"""
    eg4 = EG4Monitor()
    srp = SRPMonitor()
    
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            # Start browsers
            await eg4.start()
            await srp.start()
            
            # Login with retries
            eg4_logged_in = False
            for attempt in range(3):
                if await eg4.login():
                    eg4_logged_in = True
                    logger.info("EG4 login successful")
                    break
                logger.warning(f"EG4 login attempt {attempt + 1} failed")
                await asyncio.sleep(5)
            
            if not eg4_logged_in:
                logger.error("EG4 login failed after 3 attempts")
                raise Exception("EG4 login failed")
            
            srp_logged_in = False
            for attempt in range(3):
                if await srp.login():
                    srp_logged_in = True
                    logger.info("SRP login successful")
                    break
                logger.warning(f"SRP login attempt {attempt + 1} failed")
                await asyncio.sleep(5)
            
            if not srp_logged_in:
                logger.warning("SRP login failed - continuing without SRP data")
            
            # Reset retry count on successful connection
            retry_count = 0
            
            # Track last SRP update date
            last_srp_update_date = None
            
            # Main monitoring loop
            consecutive_failures = 0
            while True:
                try:
                    # Get EG4 data
                    eg4_data = await eg4.get_data()
                    if eg4_data:
                        monitor_data['eg4'] = eg4_data
                        monitor_data['last_update'] = datetime.now().isoformat()
                        socketio.emit('eg4_update', eg4_data)
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.warning(f"Failed to get EG4 data (attempt {consecutive_failures})")
                    
                    # Get SRP data once per day at configured time
                    if srp_logged_in:
                        # Get timezone-aware current time
                        tz_name = alert_config.get('timezone', 'UTC')
                        try:
                            tz = pytz.timezone(tz_name)
                            now = datetime.now(tz)
                        except:
                            now = datetime.now(pytz.UTC)
                        
                        # Check if it's time to update SRP (default 6 AM)
                        srp_update_hour = alert_config['thresholds'].get('peak_demand_check_hour', 6)
                        srp_update_minute = alert_config['thresholds'].get('peak_demand_check_minute', 0)
                        current_date = now.date()
                        
                        if (now.hour == srp_update_hour and 
                            now.minute == srp_update_minute and 
                            last_srp_update_date != current_date):
                            
                            logger.info(f"Updating SRP peak demand data at {srp_update_hour:02d}:{srp_update_minute:02d} {tz_name}")
                            srp_data = await srp.get_peak_demand()
                            if srp_data:
                                monitor_data['srp'] = srp_data
                                monitor_data['srp']['last_daily_update'] = now.isoformat()
                                socketio.emit('srp_update', srp_data)
                                last_srp_update_date = current_date
                                logger.info(f"SRP peak demand updated: {srp_data.get('demand', 0)}kW")
                    
                    # Check thresholds
                    check_thresholds()
                    
                    # If too many consecutive failures, restart
                    if consecutive_failures >= 5:
                        logger.error("Too many consecutive failures, restarting monitors")
                        raise Exception("Too many consecutive data fetch failures")
                    
                    # Check for manual refresh request
                    global manual_refresh_requested
                    if manual_refresh_requested:
                        manual_refresh_requested = False
                        logger.info("Manual refresh requested, fetching data immediately")
                        continue  # Skip sleep and fetch data immediately
                    
                    # Wait 60 seconds
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    # Break inner loop to trigger reconnection
                    break
            
        except Exception as e:
            logger.error(f"Monitor connection error: {e}")
            retry_count += 1
            
            if retry_count >= max_retries:
                logger.error(f"Max retries ({max_retries}) reached. Giving up.")
                break
            
            wait_time = min(60 * retry_count, 300)  # Max 5 minute wait
            logger.info(f"Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})")
            await asyncio.sleep(wait_time)
            
        finally:
            # Always cleanup
            try:
                await eg4.close()
            except:
                pass
            try:
                await srp.close()
            except:
                pass
    
    logger.error("Monitor loop exited unexpectedly")

# Background thread
monitor_thread = None

def start_monitoring():
    """Start monitoring in background thread"""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor_loop())
    
    global monitor_thread
    monitor_thread = threading.Thread(target=run)
    monitor_thread.daemon = True
    monitor_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify(monitor_data)

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    global alert_config
    
    if request.method == 'GET':
        return jsonify(alert_config)
    
    elif request.method == 'POST':
        data = request.json
        
        # Update thresholds
        if 'thresholds' in data:
            alert_config['thresholds'].update(data['thresholds'])
        
        # Update email settings
        if 'email_enabled' in data:
            alert_config['email_enabled'] = data['email_enabled']
        if 'email_to' in data:
            alert_config['email_to'] = data['email_to']
        
        # Update timezone
        if 'timezone' in data:
            alert_config['timezone'] = data['timezone']
        
        # Save configuration to file
        save_config()
        
        return jsonify({'status': 'success'})

@app.route('/api/test-email')
def test_email():
    if not alert_config['email_to']:
        return jsonify({'status': 'error', 'message': 'No recipient email configured'}), 400
    
    # First check if gmail is configured
    configured, config_msg = check_gmail_configured()
    if not configured:
        return jsonify({'status': 'error', 'message': config_msg, 'gmail_configured': False}), 400
    
    # Try to send test email
    success, msg = send_alert_email('Test Alert', 'This is a test alert from EG4-SRP Monitor')
    if success:
        return jsonify({'status': 'success', 'message': msg})
    else:
        return jsonify({'status': 'error', 'message': msg}), 400

@app.route('/api/gmail-status')
def gmail_status():
    """Check if gmail-send is properly configured"""
    configured, msg = check_gmail_configured()
    return jsonify({'configured': configured, 'message': msg})

@app.route('/api/configure-gmail', methods=['POST'])
def configure_gmail_endpoint():
    """Configure Gmail credentials from web interface"""
    data = request.json
    
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    email_address = data.get('email_address', '').strip()
    app_password = data.get('app_password', '').strip()
    
    if not email_address:
        return jsonify({'status': 'error', 'message': 'Email address is required'}), 400
    
    if not app_password:
        return jsonify({'status': 'error', 'message': 'App password is required'}), 400
    
    # Basic email validation - just check for @ symbol
    if '@' not in email_address:
        return jsonify({'status': 'error', 'message': 'Invalid email address format'}), 400
    
    # Configure Gmail
    success, message = configure_gmail(email_address, app_password)
    
    if success:
        return jsonify({'status': 'success', 'message': message})
    else:
        return jsonify({'status': 'error', 'message': message}), 400

@app.route('/api/refresh-eg4', methods=['POST'])
def refresh_eg4():
    """Manual refresh of EG4 data"""
    global manual_refresh_requested, last_manual_refresh
    
    # Check if we've refreshed recently (within 30 seconds)
    if last_manual_refresh:
        time_since_refresh = (datetime.now() - last_manual_refresh).total_seconds()
        if time_since_refresh < 30:
            return jsonify({
                'status': 'error', 
                'message': f'Please wait {int(30 - time_since_refresh)} seconds before refreshing again'
            }), 429
    
    # Set the refresh flag
    manual_refresh_requested = True
    last_manual_refresh = datetime.now()
    
    return jsonify({'status': 'success', 'message': 'Refresh requested'})

@app.route('/api/refresh-srp', methods=['POST'])
def refresh_srp():
    """Manual refresh of SRP data (for initial load or testing)"""
    try:
        # Run async function in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def get_srp_data():
            srp = SRPMonitor()
            await srp.start()
            if await srp.login():
                data = await srp.get_peak_demand()
                await srp.close()
                return data
            await srp.close()
            return None
        
        srp_data = loop.run_until_complete(get_srp_data())
        loop.close()
        
        if srp_data:
            # Get timezone-aware current time
            tz_name = alert_config.get('timezone', 'UTC')
            try:
                tz = pytz.timezone(tz_name)
                now = datetime.now(tz)
            except:
                now = datetime.now(pytz.UTC)
            
            monitor_data['srp'] = srp_data
            monitor_data['srp']['last_daily_update'] = now.isoformat()
            socketio.emit('srp_update', srp_data)
            logger.info(f"SRP data manually refreshed: {srp_data.get('demand', 0)}kW")
            return jsonify({'status': 'success', 'data': srp_data})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to get SRP data'}), 500
            
    except Exception as e:
        logger.error(f"Failed to refresh SRP data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/timezone', methods=['POST'])
def update_timezone():
    """Update container timezone"""
    data = request.json
    
    if not data or 'timezone' not in data:
        return jsonify({'status': 'error', 'message': 'No timezone provided'}), 400
    
    timezone = data['timezone']
    
    # Validate timezone
    valid_timezones = [
        'UTC',
        'America/Phoenix',
        'America/Los_Angeles', 
        'America/Denver',
        'America/Chicago',
        'America/New_York'
    ]
    
    if timezone not in valid_timezones:
        return jsonify({'status': 'error', 'message': 'Invalid timezone'}), 400
    
    # Update configuration
    alert_config['timezone'] = timezone
    save_config()
    
    # Set TZ environment variable
    os.environ['TZ'] = timezone
    
    # Try to update system timezone (this may not work in container)
    try:
        # This will update the timezone for the current process
        time.tzset()
        logger.info(f"Timezone updated to {timezone}")
    except Exception as e:
        logger.error(f"Failed to update timezone: {e}")
    
    # For immediate effect in container, we need to restart the Flask app
    # This is a simple approach - in production you might want a more graceful solution
    
    # Schedule a restart after response is sent
    def restart_app():
        time.sleep(1)  # Give time for response to be sent
        os._exit(0)  # Docker will restart the container due to restart policy
    
    threading.Thread(target=restart_app).start()
    
    return jsonify({'status': 'success', 'message': f'Timezone updated to {timezone}. Container restarting...'})

@app.route('/api/logs')
def get_logs():
    """Get recent logs for display in web interface"""
    # Get parameters
    lines = request.args.get('lines', 100, type=int)
    level = request.args.get('level', 'ALL')
    
    # Filter logs by level if specified
    logs = list(log_buffer)
    if level != 'ALL':
        logs = [log for log in logs if log['level'] == level]
    
    # Get last N lines
    logs = logs[-lines:]
    
    # Add system info
    log_info = {
        'logs': logs,
        'total_buffered': len(log_buffer),
        'log_file': LOG_FILE,
        'max_size_mb': LOG_MAX_SIZE / 1024 / 1024,
        'rotation_count': LOG_BACKUP_COUNT
    }
    
    return jsonify(log_info)

@app.route('/api/logs/download')
def download_logs():
    """Download the current log file"""
    try:
        # Force flush of all handlers
        for handler in root_logger.handlers:
            handler.flush()
        
        # Check if log file exists
        if not os.path.exists(LOG_FILE):
            return jsonify({'error': 'Log file not found'}), 404
        
        # Read the log file
        with open(LOG_FILE, 'r') as f:
            content = f.read()
        
        # Create response with proper headers
        response = make_response(content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename=eg4_srp_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        return response
    except Exception as e:
        logger.error(f"Failed to download logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Clear the in-memory log buffer"""
    try:
        log_buffer.clear()
        logger.info("Log buffer cleared by user request")
        return jsonify({'status': 'success', 'message': 'Log buffer cleared'})
    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    emit('connected', {'data': 'Connected to EG4-SRP Monitor'})
    # Send current data
    if monitor_data['eg4']:
        emit('eg4_update', monitor_data['eg4'])
    if monitor_data['srp']:
        emit('srp_update', monitor_data['srp'])

if __name__ == '__main__':
    logger.info("=== EG4-SRP Monitor Starting ===")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info(f"Max log size: {LOG_MAX_SIZE / 1024 / 1024}MB with {LOG_BACKUP_COUNT} rotations")
    
    # Load saved configuration
    load_config()
    
    # Set timezone from configuration
    if alert_config.get('timezone'):
        os.environ['TZ'] = alert_config['timezone']
        try:
            time.tzset()
            logger.info(f"Timezone set to {alert_config['timezone']}")
        except Exception as e:
            logger.warning(f"Failed to set timezone: {e}")
    
    # Start monitoring on startup if credentials exist
    if os.getenv('EG4_USERNAME') and os.getenv('EG4_PASSWORD'):
        logger.info("Credentials found, starting monitoring thread")
        start_monitoring()
    else:
        logger.warning("No EG4 credentials found in environment")
    
    # Check if we're in development mode
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    if debug_mode:
        logger.info("Starting Flask application in DEVELOPMENT mode on port 5000 (auto-reload enabled)")
    else:
        logger.info("Starting Flask application in PRODUCTION mode on port 5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug_mode, allow_unsafe_werkzeug=True)