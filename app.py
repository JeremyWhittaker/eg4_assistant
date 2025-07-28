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
import csv
import glob

# Import data storage module
try:
    from data_storage import DataStorage, CachedDataStorage
    DATA_STORAGE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Data storage module not available: {e}")
    DATA_STORAGE_AVAILABLE = False

# Configure logging with rotation
LOG_FILE = './logs/eg4_srp_monitor.log'
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 3

# Create formatters
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set up root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Suppress Werkzeug production warnings
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

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

# Monitor instances (initialized in monitor_loop)
eg4_monitor = None
srp_monitor = None
enphase_monitor = None

# Global state
monitor_data = {
    'eg4': {},
    'srp': {},
    'enphase': {},
    'last_update': None
}

# Initialize data storage
data_storage = None
cached_data_storage = None

if DATA_STORAGE_AVAILABLE:
    try:
        data_storage = DataStorage()
        cached_data_storage = CachedDataStorage(data_storage)
        logger.info("Data storage initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize data storage: {e}")
        data_storage = None
        cached_data_storage = None
else:
    logger.warning("Data storage not available - running without persistence")

# Track manual refresh requests
manual_refresh_requested = False
manual_srp_refresh_requested = False
manual_csv_download_requested = False
last_manual_refresh = None

# Configuration file path
CONFIG_FILE = './config/config.json'

# Default configuration
alert_config = {
    'email_enabled': False,
    'email_to': '',  # Comma-separated list of recipients
    'timezone': 'America/Phoenix',  # Default to Phoenix timezone
    'credentials': {
        'eg4_username': '',
        'eg4_password': '',
        'srp_username': '',
        'srp_password': '',
        'enphase_username': '',
        'enphase_password': ''
    },
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
        self.username = alert_config['credentials'].get('eg4_username', '') or os.getenv('EG4_USERNAME', '')
        self.password = alert_config['credentials'].get('eg4_password', '') or os.getenv('EG4_PASSWORD', '')
        self.browser = None
        self.page = None
        self.playwright = None
        self.logged_in = False
        self.session_start_time = None
    
    def update_credentials(self, username, password):
        """Update credentials and reset login state"""
        self.username = username
        self.password = password
        self.logged_in = False
        self.session_start_time = None
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
        )
        self.page = await self.browser.new_page()
        # Set longer default timeout for all page operations (2 minutes)
        self.page.set_default_timeout(120000)
        self.session_start_time = time.time()
        
    async def is_logged_in(self):
        """Check if we're still logged in by looking at the current URL"""
        try:
            current_url = self.page.url
            # If we're on login page or session expired, we're not logged in
            if 'login' in current_url or 'expired' in current_url:
                return False
            # Also check if session is too old (prevent stale sessions)
            if self.session_start_time and (time.time() - self.session_start_time) > self.max_session_duration:
                logger.info("Session too old, forcing re-login")
                return False
            return self.logged_in
        except:
            return False
        
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
                self.logged_in = True
                self.session_start_time = time.time()
            else:
                logger.warning("EG4 login failed - still on login page")
                self.logged_in = False
            return success
        except Exception as e:
            logger.error(f"EG4 login error: {e}", exc_info=True)
            self.logged_in = False
            return False
    
    async def get_data(self):
        try:
            # Check if we need to login first
            if not await self.is_logged_in():
                logger.info("Not logged in or session expired, attempting login")
                if not await self.login():
                    logger.error("Failed to login to EG4")
                    return None
            
            # If already on the monitor page, just refresh instead of full navigation
            current_url = self.page.url
            if 'monitor/inverter' in current_url:
                logger.debug("Already on monitor page, refreshing data")
                await self.page.reload(wait_until='networkidle')
            else:
                logger.debug("Navigating to monitor page")
                await self.page.goto('https://monitor.eg4electronics.com/WManage/web/monitor/inverter', wait_until='networkidle')
            
            await asyncio.sleep(2)  # Shorter wait since we're often just refreshing
            
            # Wait for data to load with better debugging
            data_loaded = False
            for i in range(10):
                soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
                if soc and soc != '--':
                    data_loaded = True
                    break
                logger.debug(f"Waiting for EG4 data to load... attempt {i+1}/10, SOC: {soc}")
                await asyncio.sleep(1)
            
            if not data_loaded:
                logger.warning("EG4 data did not load after 10 seconds")
            
            # Extract data with debug info
            data = await self.page.evaluate("""
                () => {
                    const cleanText = (text) => {
                        if (!text || text === '--') return '0';
                        return text.trim().replace(/[^0-9.-]/g, '');
                    };
                    
                    // Get raw values for debugging
                    const rawSoc = document.querySelector('.socText')?.textContent;
                    const rawBatteryPower = document.querySelector('.batteryPowerText')?.textContent;
                    const rawBatteryVoltage = document.querySelector('.vbatText')?.textContent;
                    const rawGridPower = document.querySelector('.gridPowerText')?.textContent;
                    const rawGridVoltage = document.querySelector('.vacText')?.textContent;
                    const rawLoadPower = document.querySelector('.consumptionPowerText')?.textContent;
                    
                    // Get individual PV string data
                    const rawPv1Power = document.querySelector('.pv1PowerText')?.textContent;
                    const rawPv1Voltage = document.querySelector('.vpv1Text')?.textContent;
                    const rawPv2Power = document.querySelector('.pv2PowerText')?.textContent;
                    const rawPv2Voltage = document.querySelector('.vpv2Text')?.textContent;
                    const rawPv3Power = document.querySelector('.pv3PowerText')?.textContent;
                    const rawPv3Voltage = document.querySelector('.vpv3Text')?.textContent;
                    
                    // Calculate individual string values
                    const pv1Power = parseInt(cleanText(rawPv1Power)) || 0;
                    const pv1Voltage = parseFloat(cleanText(rawPv1Voltage)) || 0;
                    const pv2Power = parseInt(cleanText(rawPv2Power)) || 0;
                    const pv2Voltage = parseFloat(cleanText(rawPv2Voltage)) || 0;
                    const pv3Power = parseInt(cleanText(rawPv3Power)) || 0;
                    const pv3Voltage = parseFloat(cleanText(rawPv3Voltage)) || 0;
                    
                    // Calculate total PV power
                    const totalPvPower = pv1Power + pv2Power + pv3Power;
                    
                    return {
                        battery: {
                            soc: parseInt(cleanText(rawSoc)) || 0,
                            power: parseInt(cleanText(rawBatteryPower)) || 0,
                            voltage: parseFloat(cleanText(rawBatteryVoltage)) || 0
                        },
                        pv: {
                            total_power: totalPvPower,
                            power: totalPvPower, // Keep for backward compatibility
                            strings: {
                                pv1: { power: pv1Power, voltage: pv1Voltage },
                                pv2: { power: pv2Power, voltage: pv2Voltage },
                                pv3: { power: pv3Power, voltage: pv3Voltage }
                            }
                        },
                        grid: {
                            power: parseInt(cleanText(rawGridPower)) || 0,
                            voltage: parseFloat(cleanText(rawGridVoltage)) || 0
                        },
                        load: {
                            power: parseInt(cleanText(rawLoadPower)) || 0
                        },
                        debug: {
                            rawSoc: rawSoc,
                            rawBatteryPower: rawBatteryPower,
                            rawBatteryVoltage: rawBatteryVoltage,
                            rawPv1Power: rawPv1Power,
                            rawPv1Voltage: rawPv1Voltage,
                            rawPv2Power: rawPv2Power,
                            rawPv2Voltage: rawPv2Voltage,
                            rawPv3Power: rawPv3Power,
                            rawPv3Voltage: rawPv3Voltage,
                            rawGridPower: rawGridPower,
                            rawGridVoltage: rawGridVoltage,
                            rawLoadPower: rawLoadPower
                        }
                    };
                }
            """)
            
            # Log debug info if all values are zero
            if data and is_valid_eg4_data(data):
                pv_strings = data['pv']['strings']
                pv_details = f"PV1:{pv_strings['pv1']['power']}W, PV2:{pv_strings['pv2']['power']}W, PV3:{pv_strings['pv3']['power']}W"
                logger.debug(f"EG4 data extracted successfully: SOC={data['battery']['soc']}%, PV Total={data['pv']['total_power']}W ({pv_details})")
            elif data:
                logger.warning(f"EG4 data all zeros - raw values: {data.get('debug', {})}")
            
            return data
            
        except Exception as e:
            error_msg = str(e).lower()
            # Check if it's a session/navigation error that requires re-login
            if 'timeout' in error_msg or 'navigation' in error_msg or 'login' in error_msg:
                logger.warning(f"Session appears to have expired: {e}")
                self.logged_in = False
            else:
                logger.error(f"EG4 data extraction error: {e}", exc_info=True)
            return None
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

class EnphaseMonitor:
    def __init__(self):
        self.username = alert_config['credentials'].get('enphase_username', '') or os.getenv('ENPHASE_USERNAME', '')
        self.password = alert_config['credentials'].get('enphase_password', '') or os.getenv('ENPHASE_PASSWORD', '')
        self.browser = None
        self.page = None
        self.playwright = None
        self.logged_in = False
        self.last_login_time = None
        self.system_url = "https://enlighten.enphaseenergy.com/systems/5815605/"
    
    def update_credentials(self, username, password):
        """Update credentials"""
        self.username = username
        self.password = password
        self.logged_in = False  # Force re-login with new credentials
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
        )
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(120000)  # 2 minute timeout
        
    async def is_logged_in(self):
        """Check if currently logged in to Enphase"""
        if not self.page:
            return False
            
        try:
            # Check if session has expired (more than 2 hours)
            if self.last_login_time:
                time_since_login = datetime.now() - self.last_login_time
                if time_since_login.total_seconds() > 7200:  # 2 hours
                    logger.info("Enphase session expired (2+ hours), forcing re-login")
                    self.logged_in = False
                    return False
            
            # Navigate to the system page to test session
            await self.page.goto(self.system_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Check if we can access the summary data (means we're logged in)
            summary_element = await self.page.query_selector('#summary')
            if summary_element:
                return True
            
            # If we see login elements, session is invalid
            page_content = await self.page.content()
            if 'sign in' in page_content.lower() or 'login' in page_content.lower():
                logger.info("Enphase session invalid - login required")
                self.logged_in = False
                return False
                
        except Exception as e:
            logger.warning(f"Error checking Enphase login status: {e}")
            self.logged_in = False
            return False
        
        return False

    async def login(self):
        try:
            await self.page.goto('https://enlighten.enphaseenergy.com/', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Look for sign in button and click it
            sign_in_button = await self.page.query_selector('a[href*="signin"], button:has-text("Sign In"), a:has-text("Sign In")')
            if sign_in_button:
                await sign_in_button.click()
                await asyncio.sleep(3)
            
            # Fill in credentials
            logger.info("Attempting Enphase login...")
            username_field = await self.page.query_selector('input[name="username"], input[type="email"], input[id*="email"], input[id*="username"]')
            password_field = await self.page.query_selector('input[name="password"], input[type="password"]')
            
            if not username_field or not password_field:
                logger.error("Could not find Enphase login fields")
                return False
            
            await username_field.fill(self.username)
            await password_field.fill(self.password)
            
            # Submit the form
            submit_button = await self.page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Sign In")')
            if submit_button:
                await submit_button.click()
            else:
                await password_field.press('Enter')
            
            await asyncio.sleep(5)
            
            # Check if login was successful by navigating to our system
            await self.page.goto(self.system_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # Verify we can access the summary section
            summary_element = await self.page.query_selector('#summary')
            login_success = summary_element is not None
            
            if login_success:
                self.logged_in = True
                self.last_login_time = datetime.now()
                logger.info("Enphase login successful")
            else:
                self.logged_in = False
                logger.error("Enphase login failed - could not access system page")
            
            return login_success
            
        except Exception as e:
            logger.error(f"Enphase login error: {e}")
            self.logged_in = False
            return False
    
    async def get_data(self):
        """Extract Enphase system data from the summary tab"""
        try:
            # Make sure we're on the right page
            await self.page.goto(self.system_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # Extract data using the provided selectors
            data = {}
            
            # Today's energy production
            today_energy_elem = await self.page.query_selector('#energy_today .formatted-value')
            if today_energy_elem:
                today_energy_text = await today_energy_elem.get_attribute('data-value')
                data['today_energy_kwh'] = float(today_energy_text) if today_energy_text else 0
            
            # Peak power today
            peak_power_elem = await self.page.query_selector('#peak_power .formatted-value')
            if peak_power_elem:
                peak_power_text = await peak_power_elem.get_attribute('data-value')
                data['peak_power_kw'] = float(peak_power_text) if peak_power_text else 0
            
            # Peak power time
            peak_time_elem = await self.page.query_selector('#peak_power .time')
            if peak_time_elem:
                peak_time_text = await peak_time_elem.text_content()
                data['peak_power_time'] = peak_time_text.replace('at ', '').strip() if peak_time_text else ''
            
            # Latest power output
            latest_power_elem = await self.page.query_selector('#latest_power .formatted-value')
            if latest_power_elem:
                latest_power_text = await latest_power_elem.get_attribute('data-value')
                data['latest_power_w'] = float(latest_power_text) if latest_power_text else 0
            
            # Latest power time
            latest_time_elem = await self.page.query_selector('#latest_power .time')
            if latest_time_elem:
                latest_time_text = await latest_time_elem.text_content()
                data['latest_power_time'] = latest_time_text.replace('at ', '').strip() if latest_time_text else ''
            
            # Past 7 days energy
            seven_days_elem = await self.page.query_selector('#energy_last_7_days .formatted-value')
            if seven_days_elem:
                seven_days_text = await seven_days_elem.get_attribute('data-value')
                data['past_7_days_kwh'] = float(seven_days_text) if seven_days_text else 0
            
            # Month to date energy
            month_elem = await self.page.query_selector('#energy_month .formatted-value')
            if month_elem:
                month_text = await month_elem.get_attribute('data-value')
                data['month_to_date_kwh'] = float(month_text) if month_text else 0
            
            # Lifetime energy
            lifetime_elem = await self.page.query_selector('#energy_lifetime .formatted-value')
            if lifetime_elem:
                lifetime_text = await lifetime_elem.get_attribute('data-value')
                data['lifetime_mwh'] = float(lifetime_text) if lifetime_text else 0
            
            # AC Voltage
            voltage_elem = await self.page.query_selector('#system_ac_voltage .formatted-value')
            if voltage_elem:
                voltage_text = await voltage_elem.get_attribute('data-value')
                data['microinverter_ac_voltage_v'] = float(voltage_text) if voltage_text else 0
            
            # Add timestamp
            data['last_update'] = datetime.now().isoformat()
            
            logger.debug(f"Enphase data extracted: {data}")
            return data
            
        except Exception as e:
            logger.error(f"Error extracting Enphase data: {e}")
            return None
    
    async def stop(self):
        """Clean up resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error stopping Enphase monitor: {e}")

class SRPMonitor:
    def __init__(self):
        self.username = alert_config['credentials'].get('srp_username', '') or os.getenv('SRP_USERNAME', '')
        self.password = alert_config['credentials'].get('srp_password', '') or os.getenv('SRP_PASSWORD', '')
        self.browser = None
        self.page = None
        self.playwright = None
        self.logged_in = False
        self.last_login_time = None
    
    def update_credentials(self, username, password):
        """Update credentials"""
        self.username = username
        self.password = password
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
        )
        self.page = await self.browser.new_page()
        # Set longer default timeout for all page operations (2 minutes)
        self.page.set_default_timeout(120000)
        
    async def is_logged_in(self):
        """Check if currently logged in to SRP"""
        if not self.page:
            return False
            
        try:
            # Check if session has expired (more than 2 hours)
            if self.last_login_time:
                time_since_login = datetime.now() - self.last_login_time
                if time_since_login.total_seconds() > 7200:  # 2 hours
                    logger.info("SRP session expired (2+ hours), forcing re-login")
                    self.logged_in = False
                    return False
            
            # Navigate to a protected page to test session
            current_url = self.page.url
            await self.page.goto('https://myaccount.srpnet.com/power/myaccount/usage', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # If we're redirected to login page or see login elements, session is invalid
            page_content = await self.page.content()
            if ('username' in page_content and 'password' in page_content) or 'login' in self.page.url.lower():
                logger.info("SRP session invalid - login required")
                self.logged_in = False
                return False
            
            # If we can access the usage page, we're logged in
            if 'usage' in self.page.url or 'dashboard' in self.page.url:
                return True
                
        except Exception as e:
            logger.warning(f"Error checking SRP login status: {e}")
            self.logged_in = False
            return False
        
        return False

    async def login(self):
        try:
            await self.page.goto('https://myaccount.srpnet.com/power', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Check if already logged in
            if 'dashboard' in self.page.url:
                self.logged_in = True
                self.last_login_time = datetime.now()
                logger.info("SRP already logged in")
                return True
                
            # Login
            logger.info("Attempting SRP login...")
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            await asyncio.sleep(5)
            
            # Verify login success
            login_success = 'dashboard' in self.page.url or 'myaccount' in self.page.url
            if login_success:
                self.logged_in = True
                self.last_login_time = datetime.now()
                logger.info("SRP login successful")
            else:
                self.logged_in = False
                logger.error("SRP login failed - incorrect credentials or page structure changed")
            
            return login_success
            
        except Exception as e:
            logger.error(f"SRP login error: {e}")
            self.logged_in = False
            return False
    
    async def get_peak_demand(self):
        try:
            await self.page.goto('https://myaccount.srpnet.com/power/myaccount/usage', wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Extract peak demand
            demand_data = await self.page.evaluate("""
                () => {
                    // Try multiple selectors for peak demand
                    let demandValue = '0';
                    let debugInfo = {};
                    
                    // Primary selector
                    const srpRedText = document.querySelector('.srp-red-text strong');
                    if (srpRedText) {
                        demandValue = srpRedText.textContent.trim();
                        debugInfo.foundWith = 'srp-red-text strong';
                    } else {
                        // Try alternative selectors
                        const altSelectors = [
                            '.peak-demand-value',
                            '.demand-value',
                            '.current-peak strong',
                            '[data-testid="peak-demand"]',
                            '.usage-summary .value'
                        ];
                        
                        for (const selector of altSelectors) {
                            const elem = document.querySelector(selector);
                            if (elem) {
                                demandValue = elem.textContent.trim();
                                debugInfo.foundWith = selector;
                                break;
                            }
                        }
                        
                        // If still not found, look for any element containing "kW"
                        if (demandValue === '0') {
                            const allElements = document.querySelectorAll('*');
                            for (const elem of allElements) {
                                if (elem.textContent && elem.textContent.includes('kW') && 
                                    !elem.textContent.includes('Peak') && 
                                    elem.children.length === 0) {
                                    const match = elem.textContent.match(/(\\d+\\.?\\d*)\\s*kW/);
                                    if (match) {
                                        demandValue = match[1];
                                        debugInfo.foundWith = 'kW text search';
                                        debugInfo.elementText = elem.textContent;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    
                    // Clean the value - remove 'kW' if present
                    demandValue = demandValue.replace(/kW/gi, '').trim();
                    
                    return {
                        demand: parseFloat(demandValue) || 0,
                        timestamp: new Date().toISOString(),
                        debug: debugInfo
                    };
                }
            """)
            
            # Log debug info if available
            if 'debug' in demand_data and demand_data['debug']:
                logger.info(f"SRP peak demand debug: {demand_data['debug']}")
            
            return demand_data
            
        except Exception as e:
            logger.error(f"SRP data error: {e}")
            return {'demand': 0}
    
    async def download_csv_data(self):
        """Download all CSV chart types from SRP"""
        chart_types = {
            'net': 'Net energy',
            'generation': 'Generation', 
            'usage': 'Usage',
            'demand': 'Demand'
        }
        
        downloaded_files = {}
        downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        try:
            # Navigate to the usage page first to ensure we're in the right place
            logger.info("Navigating to SRP usage page for CSV downloads...")
            await self.page.goto('https://myaccount.srpnet.com/power/myaccount/usage', wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Log current page for debugging
            current_url = self.page.url
            logger.info(f"Current page: {current_url}")
            
            logger.info("Starting SRP CSV download for all chart types")
            
            for chart_key, chart_name in chart_types.items():
                try:
                    logger.info(f"Downloading {chart_name} data...")
                    
                    # Look for and click the chart type button using the correct classes
                    # First try the specific button with chart-type-btn class
                    chart_selector = f'button.chart-type-btn:has-text("{chart_name}")'
                    chart_button = await self.page.query_selector(chart_selector)
                    
                    if not chart_button:
                        # Try alternative selectors
                        alt_selectors = [
                            f'button.chart-type-btn.button-focus:has-text("{chart_name}")',
                            f'button:has-text("{chart_name}")',
                            f'a:has-text("{chart_name}")',
                            f'[title*="{chart_name}"]',
                            f'[data-chart-type="{chart_key}"]',
                            f'[data-view="{chart_key}"]'
                        ]
                        for selector in alt_selectors:
                            chart_button = await self.page.query_selector(selector)
                            if chart_button:
                                break
                    
                    if chart_button:
                        # Log which selector worked for debugging
                        button_text = await chart_button.text_content()
                        logger.info(f"Found {chart_name} button with text '{button_text}', clicking...")
                        await chart_button.click()
                        await asyncio.sleep(3)  # Wait for chart to load
                        logger.info(f"Successfully clicked {chart_name} button, chart should be loading...")
                    else:
                        logger.warning(f"Could not find {chart_name} button with any selector, trying to export anyway...")
                        # Log available buttons for debugging
                        try:
                            all_buttons = await self.page.query_selector_all('button')
                            button_texts = []
                            for btn in all_buttons[:10]:  # Just first 10 buttons
                                text = await btn.text_content()
                                if text and text.strip():
                                    button_texts.append(text.strip())
                            logger.debug(f"Available buttons on page: {button_texts}")
                        except:
                            pass
                    
                    # Look for the Export to Excel button with multiple selectors
                    export_selectors = [
                        'button:has-text("Export to Excel")',
                        'button.btn.srp-btn.btn-lightblue:has-text("Export")',
                        'button:has-text("Export")',
                        'a:has-text("Export to Excel")',
                        'a:has-text("Export")'
                    ]
                    
                    export_button = None
                    for selector in export_selectors:
                        export_button = await self.page.query_selector(selector)
                        if export_button:
                            logger.info(f"Found export button using selector: {selector}")
                            break
                    
                    if not export_button:
                        logger.error(f"Export button not found for {chart_name} with any selector! Skipping...")
                        continue
                    
                    # Set up download handler with longer timeout for slow SRP exports
                    async with self.page.expect_download(timeout=60000) as download_info:
                        await export_button.click()
                        logger.info(f"Clicked export button for {chart_name}, waiting for download...")
                        download = await download_info.value
                    
                    # Save the download with chart type in filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'srp_{chart_key}_{timestamp}.csv'
                    filepath = os.path.join(downloads_dir, filename)
                    await download.save_as(filepath)
                    
                    downloaded_files[chart_key] = filepath
                    logger.info(f"{chart_name} file downloaded successfully: {filepath}")
                    
                    # Wait a bit before next download
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to download {chart_name}: {e}")
                    continue
            
            logger.info(f"SRP CSV download complete. Downloaded {len(downloaded_files)} files")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error during CSV download: {e}")
            return downloaded_files
    
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

def is_valid_eg4_data(data):
    """Check if EG4 data represents a real connection (not all zeros)"""
    if not data or not isinstance(data, dict):
        return False
    
    # Check if we have valid battery data (SOC should be reasonable)
    battery = data.get('battery', {})
    soc = battery.get('soc', 0)
    
    # Check for any non-zero power readings
    pv_power = data.get('pv', {}).get('power', 0)
    battery_voltage = battery.get('voltage', 0)
    grid_power = data.get('grid', {}).get('power', 0)
    load_power = data.get('load', {}).get('power', 0)
    
    # Valid connection indicators:
    # - SOC > 0 (battery has some charge)
    # - OR battery voltage > 10V (battery is connected)
    # - OR any significant power reading (PV, grid, or load)
    if (soc > 0 or 
        battery_voltage > 10 or 
        abs(pv_power) > 1 or 
        abs(grid_power) > 1 or 
        abs(load_power) > 1):
        return True
    
    # If all critical values are near zero, connection is likely invalid
    logger.debug(f"EG4 data validation failed - SOC:{soc}%, BattV:{battery_voltage}V, PV:{pv_power}W, Grid:{grid_power}W, Load:{load_power}W")
    return False

def is_valid_srp_data(data):
    """Check if SRP data represents a valid response"""
    if not data or not isinstance(data, dict):
        return False
    
    # Check if we have a valid demand value
    demand = data.get('demand', 0)
    
    # SRP demand should be a positive number (kW)
    # Even low usage should show some demand during monitoring
    if isinstance(demand, (int, float)) and demand >= 0:
        return True
    
    logger.debug(f"SRP data validation failed - demand: {demand}")
    return False

def is_valid_enphase_data(data):
    """Check if Enphase data represents a valid response"""
    if not data or not isinstance(data, dict):
        return False
    
    # Check for reasonable data values
    today_energy = data.get('today_energy_kwh', 0)
    latest_power = data.get('latest_power_w', 0)
    ac_voltage = data.get('microinverter_ac_voltage_v', 0)
    
    # During daylight hours, expect some production
    current_hour = datetime.now().hour
    if 8 <= current_hour <= 18:  # Daylight hours
        # At least some production expected during day, or reasonable voltage
        if today_energy > 0 or latest_power > 0 or ac_voltage > 200:
            return True
    else:
        # At night, zero production is normal, but voltage should still be reasonable
        if ac_voltage > 200 or today_energy >= 0:  # Accept any reasonable voltage or valid energy
            return True
    
    logger.debug(f"Enphase data validation failed - energy:{today_energy}kWh, power:{latest_power}W, voltage:{ac_voltage}V")
    return False

def retry_with_exponential_backoff(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff"""
    async def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)
                if result:  # Success
                    return result
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:  # Don't delay after last attempt
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        logger.error(f"All {max_retries} retry attempts failed")
        return None
    
    return wrapper

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
    
    # Check if EG4 data is valid before processing alerts
    if 'eg4' in monitor_data and monitor_data['eg4'] and is_valid_eg4_data(monitor_data['eg4']):
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
            # Grid import alert: trigger when grid power is NEGATIVE (importing from grid)
            # Positive grid power = exporting to grid, Negative grid power = importing from grid
            if grid_power < 0 and abs(grid_power) > alert_config['thresholds']['grid_import']:
                # Check if we haven't sent this alert recently (within 15 minutes)
                last_grid_alert = alert_config['last_alerts'].get('grid_import_last_alert')
                if last_grid_alert:
                    try:
                        last_alert_time = datetime.fromisoformat(last_grid_alert)
                        # Make sure both datetimes have the same timezone awareness
                        if last_alert_time.tzinfo is None and now.tzinfo is not None:
                            # Convert naive datetime to timezone-aware
                            last_alert_time = tz.localize(last_alert_time)
                        elif last_alert_time.tzinfo is not None and now.tzinfo is None:
                            # Convert timezone-aware to naive (shouldn't happen, but safe fallback)
                            last_alert_time = last_alert_time.replace(tzinfo=None)
                        
                        if (now - last_alert_time).total_seconds() < 900:  # 15 minutes
                            return  # Skip alert if sent recently
                    except Exception as e:
                        logger.warning(f"Error parsing last grid alert time: {e}")
                        # Continue with alert if we can't parse the time
                
                alerts.append(('High Grid Import', f'Grid importing {abs(grid_power)}W from utility during peak hours ({start_hour}:00-{end_hour}:00 {tz_name}, threshold: {alert_config["thresholds"]["grid_import"]}W)'))
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

def restore_data_on_startup():
    """Restore latest data from database on startup"""
    global monitor_data
    
    if not data_storage:
        logger.info("No data storage available - starting with empty data")
        return
    
    try:
        # Restore latest EG4 data
        latest_eg4 = data_storage.get_latest_eg4_data()
        if latest_eg4:
            logger.info(f"Restored EG4 data from {latest_eg4.get('timestamp')}")
            # Convert database format back to monitor format
            if latest_eg4.get('parsed_data'):
                monitor_data['eg4'] = latest_eg4['parsed_data']
                monitor_data['eg4']['last_update'] = latest_eg4['timestamp']
            else:
                # Reconstruct from individual fields
                monitor_data['eg4'] = {
                    'battery': {
                        'soc': latest_eg4.get('battery_soc', 0),
                        'power': latest_eg4.get('battery_power', 0),
                        'voltage': latest_eg4.get('battery_voltage', 0)
                    },
                    'pv': {
                        'power': latest_eg4.get('pv_power', 0),
                        'strings': {
                            'pv1': {'power': latest_eg4.get('pv1_power', 0), 'voltage': latest_eg4.get('pv1_voltage', 0)},
                            'pv2': {'power': latest_eg4.get('pv2_power', 0), 'voltage': latest_eg4.get('pv2_voltage', 0)},
                            'pv3': {'power': latest_eg4.get('pv3_power', 0), 'voltage': latest_eg4.get('pv3_voltage', 0)}
                        }
                    },
                    'grid': {
                        'power': latest_eg4.get('grid_power', 0),
                        'voltage': latest_eg4.get('grid_voltage', 0)
                    },
                    'load': {
                        'power': latest_eg4.get('load_power', 0)
                    },
                    'last_update': latest_eg4['timestamp']
                }
        
        # Restore latest SRP data
        latest_srp = data_storage.get_latest_srp_data()
        if latest_srp:
            logger.info(f"Restored SRP data from {latest_srp.get('date')}")
            if latest_srp.get('parsed_data'):
                monitor_data['srp'] = latest_srp['parsed_data']
            else:
                monitor_data['srp'] = {
                    'demand': latest_srp.get('peak_demand', 0),
                    'last_daily_update': latest_srp.get('created_at')
                }
        
        logger.info("Data restoration completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to restore data on startup: {e}")

async def monitor_loop():
    """Main monitoring loop with automatic recovery"""
    global eg4_monitor, srp_monitor, enphase_monitor
    
    # Restore data from database on startup
    restore_data_on_startup()
    
    eg4_monitor = EG4Monitor()
    srp_monitor = SRPMonitor()
    enphase_monitor = EnphaseMonitor()
    eg4 = eg4_monitor
    srp = srp_monitor
    enphase = enphase_monitor
    
    retry_count = 0
    max_retries = 5
    eg4_started = False
    srp_started = False
    enphase_started = False
    
    while True:
        try:
            # Start browsers if not already started
            if not eg4_started:
                await eg4.start()
                eg4_started = True
                logger.info("EG4 browser started")
            
            if not srp_started:
                await srp.start()
                srp_started = True
                logger.info("SRP browser started")
            
            if not enphase_started:
                await enphase.start()
                enphase_started = True
                logger.info("Enphase browser started")
            
            # Check SRP login status and login if needed
            srp_logged_in = False
            try:
                # Check if already logged in
                if await srp.is_logged_in():
                    srp_logged_in = True
                    logger.debug("SRP session validated - already logged in")
                else:
                    # Need to login
                    for attempt in range(3):
                        if await srp.login():
                            srp_logged_in = True
                            logger.info("SRP login successful")
                            break
                        logger.warning(f"SRP login attempt {attempt + 1} failed")
                        await asyncio.sleep(5)
                    
                    if not srp_logged_in:
                        logger.error("SRP login failed after 3 attempts - continuing without SRP data")
            except Exception as e:
                logger.error(f"Error checking SRP login status: {e}")
                srp_logged_in = False
            
            # Check Enphase login status and login if needed
            enphase_logged_in = False
            try:
                # Check if already logged in
                if await enphase.is_logged_in():
                    enphase_logged_in = True
                    logger.debug("Enphase session validated - already logged in")
                else:
                    # Need to login
                    for attempt in range(3):
                        if await enphase.login():
                            enphase_logged_in = True
                            logger.info("Enphase login successful")
                            break
                        logger.warning(f"Enphase login attempt {attempt + 1} failed")
                        await asyncio.sleep(5)
                    
                    if not enphase_logged_in:
                        logger.error("Enphase login failed after 3 attempts - continuing without Enphase data")
            except Exception as e:
                logger.error(f"Error checking Enphase login status: {e}")
                enphase_logged_in = False
            
            # Reset retry count on successful connection
            retry_count = 0
            
            # Track last SRP update date
            last_srp_update_date = None
            
            # Main monitoring loop
            consecutive_failures = 0
            while True:
                try:
                    # Get EG4 data with retry logic (login handled internally if needed)
                    retry_eg4_get_data = retry_with_exponential_backoff(eg4.get_data, max_retries=2, base_delay=1)
                    eg4_data = await retry_eg4_get_data()
                    
                    if eg4_data and is_valid_eg4_data(eg4_data):
                        monitor_data['eg4'] = eg4_data
                        # Use timezone-aware timestamp for consistency - only on successful update
                        tz_name = alert_config.get('timezone', 'UTC')
                        try:
                            tz = pytz.timezone(tz_name)
                            current_time = datetime.now(tz)
                        except:
                            current_time = datetime.now(pytz.UTC)
                        monitor_data['eg4']['last_update'] = current_time.isoformat()
                        monitor_data['last_update'] = current_time.isoformat()  # Keep for backward compatibility
                        monitor_data['eg4_connected'] = True
                        socketio.emit('eg4_update', eg4_data)
                        consecutive_failures = 0
                        
                        # Store data in database
                        if data_storage:
                            try:
                                success = data_storage.store_eg4_data(eg4_data)
                                if success:
                                    logger.debug("EG4 data stored to database")
                                else:
                                    logger.warning("Failed to store EG4 data to database")
                            except Exception as e:
                                logger.error(f"Error storing EG4 data: {e}")
                        
                        logger.debug(f"EG4 data updated - SOC: {eg4_data.get('battery', {}).get('soc', 0)}%")
                    elif eg4_data:
                        consecutive_failures += 1
                        monitor_data['eg4_connected'] = False
                        logger.warning(f"EG4 data validation failed - invalid readings (attempt {consecutive_failures})")
                        logger.debug(f"EG4 invalid data: {eg4_data}")
                    else:
                        consecutive_failures += 1
                        monitor_data['eg4_connected'] = False
                        logger.error(f"Failed to get EG4 data after retries (attempt {consecutive_failures})")
                    
                    # Reset consecutive failures if we've had too many
                    if consecutive_failures >= 5:
                        logger.warning(f"Too many consecutive EG4 failures ({consecutive_failures}), forcing reconnection")
                        try:
                            await eg4.stop()
                            eg4_started = False
                            consecutive_failures = 0
                        except Exception as e:
                            logger.error(f"Error stopping EG4 monitor: {e}")
                    
                    # Get SRP data once per day at configured time OR on manual refresh OR if missing
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
                        
                        # Check for manual refresh request
                        global manual_srp_refresh_requested
                        should_update_srp = False
                        
                        if manual_srp_refresh_requested:
                            should_update_srp = True
                            manual_srp_refresh_requested = False
                            logger.info("Manual SRP refresh requested")
                        elif (now.hour == srp_update_hour and 
                              now.minute == srp_update_minute and 
                              last_srp_update_date != current_date):
                            should_update_srp = True
                            logger.info(f"Scheduled SRP update at {srp_update_hour:02d}:{srp_update_minute:02d} {tz_name}")
                        elif not monitor_data.get('srp') and last_srp_update_date is None:
                            should_update_srp = True
                            logger.info("No SRP data found, fetching initial data")
                        
                        if should_update_srp:
                            # Validate session before attempting data collection
                            if not await srp.is_logged_in():
                                logger.warning("SRP session expired, attempting re-login...")
                                for attempt in range(3):
                                    if await srp.login():
                                        logger.info("SRP re-login successful")
                                        break
                                    logger.warning(f"SRP re-login attempt {attempt + 1} failed")
                                    await asyncio.sleep(5)
                                else:
                                    logger.error("SRP re-login failed - skipping SRP update")
                                    continue
                            
                            logger.info("Updating SRP peak demand data...")
                            # Use retry logic for SRP data collection
                            retry_srp_get_data = retry_with_exponential_backoff(srp.get_peak_demand, max_retries=3, base_delay=2)
                            srp_data = await retry_srp_get_data()
                            
                            if srp_data and is_valid_srp_data(srp_data):
                                monitor_data['srp'] = srp_data
                                monitor_data['srp']['last_daily_update'] = now.isoformat()
                                socketio.emit('srp_update', srp_data)
                                last_srp_update_date = current_date
                                
                                # Store data in database
                                if data_storage:
                                    try:
                                        success = data_storage.store_srp_data(
                                            date=current_date.isoformat(),
                                            chart_type='demand',
                                            data=srp_data
                                        )
                                        if success:
                                            logger.debug("SRP data stored to database")
                                        else:
                                            logger.warning("Failed to store SRP data to database")
                                    except Exception as e:
                                        logger.error(f"Error storing SRP data: {e}")
                                
                                logger.info(f"SRP peak demand updated: {srp_data.get('demand', 0)}kW")
                                
                                # Download CSV data files after getting peak demand
                                logger.info("Downloading SRP CSV data files...")
                                csv_files = await srp.download_csv_data()
                                if csv_files:
                                    logger.info(f"Successfully downloaded {len(csv_files)} CSV files")
                                    # Store CSV download timestamp
                                    monitor_data['srp']['csv_last_update'] = now.isoformat()
                                    monitor_data['srp']['csv_files_count'] = len(csv_files)
                                else:
                                    logger.warning("Failed to download some or all CSV files")
                            elif srp_data:
                                logger.warning(f"SRP data validation failed - received invalid data: {srp_data}")
                            else:
                                logger.error("Failed to get SRP peak demand data after retries")
                    
                    # Check for manual CSV download request
                    global manual_csv_download_requested
                    if manual_csv_download_requested and srp:
                        manual_csv_download_requested = False
                        logger.info("Manual CSV download requested")
                        try:
                            # Validate session before manual download
                            if not await srp.is_logged_in():
                                logger.warning("SRP session expired for manual download, attempting re-login...")
                                for attempt in range(3):
                                    if await srp.login():
                                        logger.info("SRP re-login successful for manual download")
                                        break
                                    logger.warning(f"SRP manual download re-login attempt {attempt + 1} failed")
                                    await asyncio.sleep(5)
                                else:
                                    logger.error("SRP re-login failed - skipping manual CSV download")
                                    continue
                            
                            csv_files = await srp.download_csv_data()
                            if csv_files:
                                logger.info(f"Manual download successful: {len(csv_files)} CSV files")
                                monitor_data['srp']['csv_last_update'] = now.isoformat()
                                monitor_data['srp']['csv_files_count'] = len(csv_files)
                            else:
                                logger.warning("Manual CSV download failed")
                        except Exception as e:
                            logger.error(f"Error in manual CSV download: {e}")
                    
                    # Check thresholds
                    try:
                        check_thresholds()
                    except Exception as e:
                        logger.error(f"Error in check_thresholds(): {e}", exc_info=True)
                    
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
                    
                    # Periodic database cleanup (once per day)
                    if data_storage:
                        current_hour = datetime.now().hour
                        current_minute = datetime.now().minute
                        # Run cleanup at 3:00 AM daily
                        if current_hour == 3 and current_minute == 0:
                            try:
                                data_storage.cleanup_old_data()
                                logger.info("Daily database cleanup completed")
                            except Exception as e:
                                logger.error(f"Database cleanup failed: {e}")
                    
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
            
            # Check if it's a critical error that requires browser restart
            error_msg = str(e).lower()
            if 'browser' in error_msg or 'closed' in error_msg or 'crashed' in error_msg:
                logger.info("Browser error detected, will restart browsers")
                # Close browsers for restart
                try:
                    await eg4.close()
                    eg4_started = False
                    eg4.logged_in = False
                except:
                    pass
                try:
                    await srp.close()
                    srp_started = False
                except:
                    pass
            else:
                # For other errors, just mark as not logged in to trigger re-login
                logger.info("Non-browser error, will attempt re-login")
                eg4.logged_in = False
                if hasattr(srp, 'logged_in'):
                    srp.logged_in = False
            
            wait_time = min(60 * retry_count, 300)  # Max 5 minute wait
            logger.info(f"Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})")
            await asyncio.sleep(wait_time)
    
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
    """Get current system status"""
    status = monitor_data.copy()
    
    # Add database statistics if available
    if data_storage:
        try:
            status['database'] = data_storage.get_database_stats()
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            status['database'] = {'error': str(e)}
    
    return jsonify(status)

@app.route('/api/database/stats')
def get_database_stats():
    """Get database statistics"""
    if not data_storage:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        stats = data_storage.get_database_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical/eg4')
def get_historical_eg4():
    """Get historical EG4 data"""
    if not data_storage:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        hours = int(request.args.get('hours', 24))
        data = data_storage.get_historical_eg4_data(hours=hours)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting historical EG4 data: {e}")
        return jsonify({'error': str(e)}), 500

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
        
        # Update credentials
        if 'credentials' in data:
            alert_config['credentials'].update(data['credentials'])
            # Update monitor instances with new credentials
            global eg4_monitor, srp_monitor
            if eg4_monitor and ('eg4_username' in data['credentials'] or 'eg4_password' in data['credentials']):
                eg4_monitor.update_credentials(
                    alert_config['credentials']['eg4_username'],
                    alert_config['credentials']['eg4_password']
                )
            if srp_monitor and ('srp_username' in data['credentials'] or 'srp_password' in data['credentials']):
                srp_monitor.update_credentials(
                    alert_config['credentials']['srp_username'],
                    alert_config['credentials']['srp_password']
                )
        
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

@app.route('/api/refresh-srp')
def refresh_srp():
    """Manually refresh SRP peak demand data"""
    global manual_srp_refresh_requested
    manual_srp_refresh_requested = True
    return jsonify({'status': 'success', 'message': 'SRP refresh requested'})

@app.route('/api/download-srp-csv')
def download_srp_csv():
    """Manually trigger SRP CSV downloads"""
    global manual_csv_download_requested
    manual_csv_download_requested = True
    return jsonify({'status': 'success', 'message': 'SRP CSV download requested'})

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
        try:
            # Use timezone-aware current time for consistency
            tz_name = alert_config.get('timezone', 'UTC')
            tz = pytz.timezone(tz_name)
            current_time = datetime.now(tz)
            
            # Ensure both datetimes have the same timezone awareness
            if isinstance(last_manual_refresh, str):
                # If stored as string, parse it
                last_manual_refresh = datetime.fromisoformat(last_manual_refresh)
            
            # Make last_manual_refresh timezone-aware if it's naive
            if last_manual_refresh.tzinfo is None:
                last_manual_refresh = tz.localize(last_manual_refresh)
            elif last_manual_refresh.tzinfo != current_time.tzinfo:
                # Convert to current timezone if different
                last_manual_refresh = last_manual_refresh.astimezone(tz)
            
            time_since_refresh = (current_time - last_manual_refresh).total_seconds()
            if time_since_refresh < 30:
                return jsonify({
                    'status': 'error', 
                    'message': f'Please wait {int(30 - time_since_refresh)} seconds before refreshing again'
                }), 429
        except Exception as e:
            logger.warning(f"Error checking manual refresh time: {e}")
            # Continue with refresh if we can't compare times
    
    # Set the refresh flag with timezone-aware timestamp
    manual_refresh_requested = True
    try:
        tz_name = alert_config.get('timezone', 'UTC')
        tz = pytz.timezone(tz_name)
        last_manual_refresh = datetime.now(tz)
    except Exception as e:
        logger.warning(f"Error setting timezone-aware manual refresh time: {e}")
        last_manual_refresh = datetime.now()  # Fallback to naive datetime
    
    return jsonify({'status': 'success', 'message': 'Refresh requested'})


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

@app.route('/api/srp-chart-data')
def get_srp_chart_data():
    """Get SRP CSV data for charting"""
    try:
        # Get chart type from query parameter
        chart_type = request.args.get('type', 'net')
        valid_types = ['net', 'generation', 'usage', 'demand']
        
        if chart_type not in valid_types:
            return jsonify({'error': 'Invalid chart type'}), 400
        
        # Look for the most recent CSV file in downloads directory
        downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir, exist_ok=True)
        
        # Find CSV files for the specific chart type
        # First try new naming convention (with chart type)
        csv_files = glob.glob(os.path.join(downloads_dir, f'srp_{chart_type}_*.csv'))
        
        # If not found, try old naming convention (for backward compatibility)
        if not csv_files and chart_type == 'net':
            csv_files = glob.glob(os.path.join(downloads_dir, 'srp_usage_*.csv'))
        
        if not csv_files:
            # No CSV files found - trigger a download if we have SRP credentials
            logger.info(f"No {chart_type} CSV files found, checking if we can download...")
            
            # Check if we have any CSV files at all
            any_csv = glob.glob(os.path.join(downloads_dir, 'srp_*.csv'))
            if not any_csv:
                # No CSV files at all - suggest running the downloader
                return jsonify({
                    'error': f'No SRP data available',
                    'message': 'SRP data will be downloaded automatically at the next scheduled update, or you can run srp_csv_downloader.py manually.',
                    'needsDownload': True
                }), 404
            else:
                # We have some CSV files but not this type
                return jsonify({
                    'error': f'No {chart_type} data found',
                    'message': f'Data for {chart_type} chart type is not available. It will be downloaded at the next scheduled update.',
                    'needsDownload': True
                }), 404
        
        # Get the most recent file by filename (timestamp in filename)
        # Docker volumes can have unreliable file creation times
        latest_csv = max(csv_files)  # This works because filenames have YYYYMMDD_HHMMSS format
        logger.info(f"Reading SRP {chart_type} CSV data from: {latest_csv}")
        
        # Read CSV data - structure depends on chart type
        data = {
            'labels': [],
            'datasets': [],
            'chartType': chart_type
        }
        
        with open(latest_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            logger.info(f"CSV headers for {chart_type}: {headers}")
            
            # Initialize data arrays based on chart type
            if chart_type in ['net', 'usage']:
                # Net energy and Usage have off-peak/on-peak structure
                data['offPeak'] = []
                data['onPeak'] = []
                data['highTemp'] = []
                data['lowTemp'] = []
            elif chart_type == 'generation':
                # Generation shows total solar generation
                data['generation'] = []
                data['consumption'] = []
                data['highTemp'] = []
                data['lowTemp'] = []
            elif chart_type == 'demand':
                # Demand shows peak demand values
                data['demand'] = []
                data['peakTime'] = []
                data['highTemp'] = []
                data['lowTemp'] = []
            
            for row in reader:
                # Skip the combined total row
                if any('Combined total' in str(val) for val in row.values()):
                    continue
                
                # Get date - try different date column names
                date_str = row.get('Usage date') or row.get('Date') or row.get('Meter read date', '')
                if date_str:
                    # Parse and format date
                    try:
                        # Try different date formats
                        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y']:
                            try:
                                date_obj = datetime.strptime(date_str, fmt)
                                data['labels'].append(date_obj.strftime('%b %d'))
                                break
                            except:
                                continue
                        else:
                            data['labels'].append(date_str)
                    except:
                        data['labels'].append(date_str)
                    
                    # Parse data based on chart type
                    if chart_type in ['net', 'usage']:
                        # Get energy values (remove quotes and convert to float)
                        off_peak = row.get('Off-peak kWh', '0').replace('"', '')
                        on_peak = row.get('On-peak kWh', '0').replace('"', '')
                        
                        try:
                            data['offPeak'].append(float(off_peak))
                            data['onPeak'].append(float(on_peak))
                        except ValueError:
                            data['offPeak'].append(0)
                            data['onPeak'].append(0)
                        
                        # Get temperature values if available
                        try:
                            data['highTemp'].append(float(row.get('High temperature (F)', '0')))
                            data['lowTemp'].append(float(row.get('Low temperature (F)', '0')))
                        except ValueError:
                            data['highTemp'].append(0)
                            data['lowTemp'].append(0)
                    
                    elif chart_type == 'generation':
                        # Generation CSV has same structure as net/usage: Off-peak kWh, On-peak kWh
                        # For solar generation, we typically want to show total generation (off+on peak)
                        off_peak = row.get('Off-peak kWh', '0').replace('"', '')
                        on_peak = row.get('On-peak kWh', '0').replace('"', '')
                        
                        try:
                            off_val = float(off_peak) if off_peak else 0
                            on_val = float(on_peak) if on_peak else 0
                            total_gen = off_val + on_val
                            
                            data['generation'].append(total_gen)
                            data['consumption'].append(0)  # Generation chart doesn't show consumption
                        except ValueError:
                            data['generation'].append(0)
                            data['consumption'].append(0)
                        
                        # Get temperature values
                        try:
                            data['highTemp'].append(float(row.get('High temperature (F)', '0')))
                            data['lowTemp'].append(float(row.get('Low temperature (F)', '0')))
                        except ValueError:
                            data['highTemp'].append(0)
                            data['lowTemp'].append(0)
                    
                    elif chart_type == 'demand':
                        # Demand CSV has On-peak kW column for peak demand
                        demand_val = row.get('On-peak kW', '0').replace('"', '')
                        
                        try:
                            data['demand'].append(float(demand_val) if demand_val else 0)
                            data['peakTime'].append('')  # Time not available in this CSV format
                        except ValueError:
                            data['demand'].append(0)
                            data['peakTime'].append('')
                        
                        # Get temperature values
                        try:
                            data['highTemp'].append(float(row.get('High temperature (F)', '0')))
                            data['lowTemp'].append(float(row.get('Low temperature (F)', '0')))
                        except ValueError:
                            data['highTemp'].append(0)
                            data['lowTemp'].append(0)
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Failed to get SRP chart data: {e}")
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
    
    # Run with allow_unsafe_werkzeug=True to suppress production warnings
    # For a monitoring tool like this, Werkzeug is acceptable
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug_mode, allow_unsafe_werkzeug=True)