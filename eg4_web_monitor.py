#!/usr/bin/env python3
"""
EG4 Web Monitor - With file editor
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, time, timedelta
import os
from dotenv import load_dotenv, set_key
import json
import threading
import time as time_module
from collections import deque
import secrets
from pathlib import Path
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/eg4_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
# Reduce socket.io logging verbosity
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

# Configuration files directory
CONFIG_DIR = Path(__file__).parent
ALLOWED_FILES = ['.env', 'config.yaml', 'config.json', 'settings.json', 'alert_config.json']
ALLOWED_EXTENSIONS = ['.env', '.yaml', '.yml', '.json', '.txt', '.conf', '.ini']

# Global variables
monitor_thread = None
monitor_running = False
monitor_data = {}
credentials_verified = False
srp_data = {}

# SRP data cache
srp_cache = {
    'data': None,
    'timestamp': None
}

# SRP chart data cache
srp_chart_cache = {
    'data': None,
    'timestamp': None
}

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
        logger.info(f"EG4WebMonitor initialized with username: {self.username[:3]}***")
        
    async def start(self):
        """Start the browser"""
        self.playwright = await async_playwright().start()
        # Launch browser with extensive container-friendly options
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--single-process',  # Critical for container stability
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-features=TranslateUI',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--no-first-run',
            '--no-default-browser-check',
            '--no-service-autorun',
            '--password-store=basic',
            '--use-mock-keychain',
            '--no-zygote',
            '--disable-blink-features=AutomationControlled'
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=browser_args,
            handle_sigint=False,
            handle_sigterm=False,
            handle_sighup=False
        )
        
        # Create page with viewport
        self.page = await self.browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
    async def login(self):
        """Login to EG4 cloud monitor"""
        try:
            logger.info(f"Attempting login with username: {self.username}")
            await self.page.goto(f"{self.base_url}/WManage/web/login", wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_selector('input[name="account"]', timeout=10000)
            
            await self.page.fill('input[name="account"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            current_url = self.page.url
            login_success = 'login' not in current_url
            
            if login_success:
                logger.info("Login successful!")
            else:
                logger.error("Login failed - still on login page")
            
            return login_success
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def verify_credentials(self):
        """Quick verification of credentials"""
        try:
            await self.start()
            success = await self.login()
            await self.close()
            return success
        except Exception as e:
            logger.error(f"Credential verification error: {e}")
            if self.browser:
                await self.close()
            return False
    
    async def wait_for_data(self):
        """Wait for real data to load on the page"""
        logger.info("Waiting for data to load...")
        for i in range(30):
            await asyncio.sleep(1)
            soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
            if i % 5 == 0:
                logger.debug(f"Checking SOC ({i+1}/30): {soc}")
            if soc and soc != '--':
                logger.info(f"Data loaded! SOC: {soc}")
                return True
        logger.warning("Data did not load after 30 seconds")
        return False
    
    async def navigate_to_monitor(self):
        """Navigate to the monitor page and wait for data"""
        logger.info("Navigating to monitor page...")
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
        # Launch browser with extensive container-friendly options
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--single-process',  # Critical for container stability
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-features=TranslateUI',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--no-first-run',
            '--no-default-browser-check',
            '--no-service-autorun',
            '--password-store=basic',
            '--use-mock-keychain',
            '--no-zygote',
            '--disable-blink-features=AutomationControlled'
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=browser_args,
            handle_sigint=False,
            handle_sigterm=False,
            handle_sighup=False
        )
        
        # Create page with viewport
        self.page = await self.browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
    async def login(self):
        """Login to SRP account"""
        try:
            print(f"Attempting SRP login with username: {self.username}")
            app.logger.info(f"SRP login attempt for user: {self.username}")
            
            # Go directly to the login page
            await self.page.goto('https://myaccount.srpnet.com/power', wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)
            
            # Check if we're already logged in
            if 'Dashboard' in self.page.url and 'login' not in self.page.url.lower():
                print("Already logged in to SRP")
                app.logger.info("SRP already logged in")
                return True
            
            # Look for the login form
            try:
                # Try desktop username field first
                username_field = await self.page.wait_for_selector('input[name="username"], input#username_desktop', timeout=30000)
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
                    
                    // Extract date from cycle info or page content
                    let demandDate = new Date().toISOString().split('T')[0]; // Default to today
                    
                    // Try to find date in cycle info or nearby text
                    const dateRegex = /(\\d{1,2}\\/\\d{1,2}\\/\\d{4})/g;
                    const pageDates = bodyText.match(dateRegex) || [];
                    if (pageDates.length > 0) {
                        // Use the first date found, which is usually the demand date
                        const [month, day, year] = pageDates[0].split('/');
                        demandDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
                    }
                    
                    return {
                        demand: demandValue,
                        type: 'PEAK DEMAND',
                        cycleInfo: cycleInfo,
                        demandDate: demandDate,
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
    
    async def get_daily_usage_chart(self):
        """Extract daily usage chart data from SRP page"""
        try:
            # Make sure we're on the usage page
            current_url = self.page.url
            if 'usage' not in current_url:
                await self.page.goto(f"{self.base_url}/power/myaccount/usage", wait_until='networkidle')
                await asyncio.sleep(3)
            
            # Click on the Daily tab to show the daily usage view
            daily_tab = await self.page.query_selector('button:has-text("Daily")')
            if not daily_tab:
                # Try alternative selectors
                daily_tab = await self.page.query_selector('.MuiTab-root:has-text("Daily")')
            
            if daily_tab:
                await daily_tab.click()
                await asyncio.sleep(2)
                app.logger.info("Clicked Daily tab")
            else:
                app.logger.warning("Daily tab not found")
            
            # Debug: Take screenshot after clicking Daily tab
            await self.page.screenshot(path='/tmp/srp_usage_page_daily.png')
            app.logger.info("Screenshot saved to /tmp/srp_usage_page_daily.png")
            
            # Wait for page to fully load with longer timeout
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Click Submit button to load the daily data
            submit_button = await self.page.query_selector('button.btn.srp-btn.btn-green:has-text("Submit")')
            if submit_button:
                await submit_button.click()
                await asyncio.sleep(3)
                app.logger.info("Clicked Submit button to load daily data")
                
                # Wait for chart to load
                await self.page.wait_for_load_state('networkidle')
                
                # Scroll down to see the chart area
                await self.page.evaluate('window.scrollBy(0, 500)')
                await asyncio.sleep(1)
                
                # Take screenshot after submitting
                await self.page.screenshot(path='/tmp/srp_usage_page_after_submit.png')
                app.logger.info("Screenshot saved to /tmp/srp_usage_page_after_submit.png")
            else:
                app.logger.warning("Submit button not found")
            
            # First, try to extract chart data directly without clicking button
            # The chart might already be visible after Submit
            chart_visible = await self.page.evaluate("""
                () => {
                    // Look for chart elements
                    const chartButtons = document.querySelectorAll('.chart-type-btn');
                    const hasChart = chartButtons.length > 0;
                    
                    // Check if any chart SVG or canvas is visible
                    const svgChart = document.querySelector('svg.recharts-surface');
                    const canvasChart = document.querySelector('canvas#chart');
                    
                    return {
                        hasChartButtons: hasChart,
                        buttonCount: chartButtons.length,
                        hasSvgChart: !!svgChart,
                        hasCanvasChart: !!canvasChart
                    };
                }
            """)
            
            app.logger.info(f"Chart visibility check: {chart_visible}")
            
            # If chart buttons are already visible, skip clicking "View data table"
            if chart_visible.get('hasChartButtons', 0) > 0:
                app.logger.info("Chart already visible, skipping 'View data table' button")
                view_chart_button = None
            else:
                # Try to find and click "View data table" button
                view_chart_button = None
                
                # First scroll to make sure button is in view
                await self.page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const viewButton = buttons.find(btn => 
                            btn.textContent.includes('View data table') || 
                            btn.textContent.includes('View as data table')
                        );
                        if (viewButton) {
                            viewButton.scrollIntoView({block: 'center', behavior: 'smooth'});
                        }
                    }
                """)
                await asyncio.sleep(1)
                
                # Now try to find the button
                button_selectors = [
                    'button:has-text("View data table")',
                    'button:has-text("View as data table")'
                ]
                
                for selector in button_selectors:
                    try:
                        view_chart_button = await self.page.query_selector(selector)
                        if view_chart_button:
                            app.logger.info(f"Found button with selector: {selector}")
                            break
                    except:
                        continue
            
            # Initialize data structure first
            chart_data = {
                'dates': [],
                'netEnergy': [],
                'generation': [],
                'usage': [],
                'demand': [],
                'offPeak': [],
                'onPeak': [],
                'temperatures': {
                    'high': [],
                    'low': []
                },
                'dateRange': '',
                'chartAvailable': True
            }
            
            # At this point, the chart should be visible
            # Try to extract data directly from the chart visualization
            chart_info = await self.page.evaluate("""
                () => {
                    // Look for chart data
                    const result = {
                        dates: [],
                        values: [],
                        chartType: 'unknown'
                    };
                    
                    // Try to find x-axis labels (dates)
                    const xAxisTexts = document.querySelectorAll('text');
                    const datePattern = /^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2}$/;
                    
                    xAxisTexts.forEach(text => {
                        const content = text.textContent.trim();
                        if (datePattern.test(content)) {
                            result.dates.push(content);
                        }
                    });
                    
                    // Try to find the bars/data points
                    const bars = document.querySelectorAll('rect[fill], .recharts-bar rect, .bar-chart rect');
                    const barData = [];
                    bars.forEach(bar => {
                        const height = parseFloat(bar.getAttribute('height') || '0');
                        const y = parseFloat(bar.getAttribute('y') || '0');
                        const fill = bar.getAttribute('fill') || '';
                        if (height > 0) {
                            barData.push({ height, y, fill });
                        }
                    });
                    
                    // Check which chart type is selected
                    const selectedButton = document.querySelector('.chart-type-btn-selected');
                    if (selectedButton) {
                        result.chartType = selectedButton.textContent.trim().toLowerCase();
                    }
                    
                    result.barCount = barData.length;
                    result.dateCount = result.dates.length;
                    
                    return result;
                }
            """)
            
            app.logger.info(f"Chart info extraction: {chart_info}")
            
            # Don't use chart x-axis labels as dates - they'll be replaced with actual dates from table
            # if chart_info.get('dates'):
            #     chart_data['dates'] = chart_info['dates']
            
            # Define the chart types to extract
            chart_types = [
                ('Net energy', 'netEnergy'),
                ('Generation', 'generation'),
                ('Usage', 'usage'),
                ('Demand', 'demand')
            ]
            
            # Check if we're already in table view or need to click to table view
            view_table_button = None
            if chart_visible.get('hasChartButtons', 0) > 0:
                app.logger.info("Chart buttons are visible, skipping view table button search")
            else:
                view_table_button = await self.page.query_selector('button:has-text("View as table")')
                if not view_table_button:
                    view_table_button = await self.page.query_selector('button:has-text("View data table")')
            
            # If neither found, check if already in table view or need to click "View as chart" to toggle
            is_table_view = await self.page.query_selector('table')
            if not is_table_view and not view_table_button:
                # We might be in chart view, check for the "View as chart" button
                view_chart_button = await self.page.query_selector('button:has-text("View as chart")')
                if view_chart_button:
                    app.logger.info("Found 'View as chart' button, page is already in table view")
                    view_table_button = None  # Don't need to click anything
            
            if view_table_button:
                await view_table_button.click()
                await asyncio.sleep(2)
                app.logger.info("Clicked 'View as data table' button")
                
                # Extract table data
                table_data = await self.page.evaluate("""
                    () => {
                        const result = {
                            headers: [],
                            rows: [],
                            tableFound: false,
                            tableId: null,
                            tableClass: null
                        };
                        
                        // Find the data table - try multiple selectors
                        let table = document.querySelector('table#usageDataTable');
                        if (!table) table = document.querySelector('table[aria-label*="usage"]');
                        if (!table) table = document.querySelector('table.data-table');
                        if (!table) table = document.querySelector('table');
                        
                        if (!table) return result;
                        
                        result.tableFound = true;
                        result.tableId = table.id || 'none';
                        result.tableClass = table.className || 'none';
                        
                        // Get headers
                        const headerCells = table.querySelectorAll('thead th, thead td');
                        headerCells.forEach(cell => {
                            result.headers.push(cell.textContent.trim());
                        });
                        
                        // Get rows
                        const rows = table.querySelectorAll('tbody tr');
                        rows.forEach((row, idx) => {
                            const rowData = [];
                            const cells = row.querySelectorAll('td');
                            cells.forEach(cell => {
                                // Get the text content and clean it up
                                let text = cell.textContent.trim();
                                // Also check for any input elements
                                const input = cell.querySelector('input');
                                if (input && input.value) {
                                    text = input.value.trim();
                                }
                                rowData.push(text);
                            });
                            if (rowData.length > 0) {
                                result.rows.push(rowData);
                            }
                        });
                        
                        return result;
                    }
                """)
                
                app.logger.info(f"Table data extracted: {len(table_data.get('rows', []))} rows, headers: {table_data.get('headers', [])}")
                app.logger.info(f"Table info: found={table_data.get('tableFound')}, id={table_data.get('tableId')}, class={table_data.get('tableClass')}")
                
                # Log first few rows for debugging
                if table_data.get('rows'):
                    for i, row in enumerate(table_data['rows'][:3]):
                        app.logger.info(f"Row {i}: {row}")
                
                # Parse the table data
                if table_data.get('rows'):
                    # Determine which columns contain what based on headers
                    headers = table_data.get('headers', [])
                    date_col = 0  # Usually first column
                    value_cols = []
                    
                    # Find value columns based on header names
                    for i, header in enumerate(headers):
                        header_lower = header.lower()
                        # Skip date columns
                        if 'date' in header_lower:
                            continue
                        # Look for kWh columns
                        if 'kwh' in header_lower:
                            value_cols.append(i)
                    
                    # If no value columns found, look for numeric columns
                    if not value_cols:
                        # For the net energy table, we're looking for the Total kWh column
                        for i, header in enumerate(headers):
                            if 'total' in header.lower():
                                value_cols = [i]
                                break
                    
                    app.logger.info(f"Value columns: {value_cols}")
                    
                    # Find which column has the usage date (not meter read date)
                    usage_date_col = 1  # Default to column 1
                    for i, header in enumerate(headers):
                        if 'usage date' in header.lower():
                            usage_date_col = i
                            break
                    
                    for row in table_data['rows']:
                        if len(row) > usage_date_col:
                            # Extract date from usage date column
                            date = row[usage_date_col]
                            if date and date not in chart_data['dates']:
                                chart_data['dates'].append(date)
                            
                            # For Net Energy view, we want the Total kWh
                            if 'total' in headers[value_cols[0]].lower() if value_cols else False:
                                try:
                                    # The total column shows the net energy value
                                    value_text = row[value_cols[0]]
                                    # Handle negative values with parentheses
                                    if '(' in value_text and ')' in value_text:
                                        value_text = '-' + value_text.replace('(', '').replace(')', '')
                                    value = float(value_text.replace(',', '').replace(' kWh', '').replace('kWh', ''))
                                    chart_data['netEnergy'].append(value)
                                except Exception as e:
                                    app.logger.warning(f"Error parsing net energy value: {e}, row: {row}")
                            else:
                                # For other views, extract all kWh columns
                                try:
                                    # Extract temperature values
                                    if len(row) >= 9:  # Has temperature columns
                                        high_temp = float(row[7])
                                        low_temp = float(row[8])
                                        if len(chart_data['temperatures']['high']) < len(chart_data['dates']):
                                            chart_data['temperatures']['high'].append(high_temp)
                                            chart_data['temperatures']['low'].append(low_temp)
                                    
                                    # Extract energy values based on available columns
                                    if len(row) >= 7:  # Has all energy columns
                                        super_off_peak = float(row[2])
                                        off_peak = float(row[3])
                                        shoulder = float(row[4])
                                        on_peak = float(row[5])
                                        total = float(row[6])
                                        
                                        # Store off-peak (includes super off-peak) and on-peak
                                        chart_data['offPeak'].append(super_off_peak + off_peak + shoulder)
                                        chart_data['onPeak'].append(on_peak)
                                        # Calculate usage as sum of all rate periods since total column is often 0
                                        calculated_usage = abs(super_off_peak) + abs(off_peak) + abs(shoulder) + abs(on_peak)
                                        chart_data['usage'].append(calculated_usage if total == 0 else total)
                                except Exception as e:
                                    app.logger.warning(f"Error parsing row values: {e}, row: {row}")
                
                # Click back to chart view if we switched to table view
                view_chart_button = await self.page.query_selector('button:has-text("View as chart")')
                if view_chart_button:
                    await view_chart_button.click()
                    await asyncio.sleep(1)
                else:
                    # Try alternative button text
                    view_chart_button = await self.page.query_selector('button:has-text("View chart")')
                    if view_chart_button:
                        await view_chart_button.click()
                        await asyncio.sleep(1)
            else:
                app.logger.warning("'View as data table' button not found")
            
            # Skip clicking through chart types if we already have the data
            if chart_data['offPeak'] and chart_data['onPeak'] and len(chart_data['offPeak']) > 0:
                app.logger.info("Data already extracted from initial table, skipping chart type buttons")
            elif not view_table_button and chart_visible.get('hasChartButtons', 0) > 0:
                # If chart is visible but no table button, we might already have the data visible
                app.logger.info("Chart is visible but no table button found, returning available data")
                # Use the dates from chart_info if available
                if chart_info.get('dates'):
                    chart_data['dates'] = chart_info['dates']
                    app.logger.info(f"Returning chart data with {len(chart_data['dates'])} dates from chart visualization")
                    # Set a flag to indicate limited data
                    chart_data['dataLimited'] = True
                    chart_data['message'] = "Chart is visible but detailed data extraction is not available"
                else:
                    app.logger.warning("No data extracted, chart might be empty")
            else:
                # Now extract data for each chart type by clicking buttons
                app.logger.info(f"Starting to extract data for chart types: {[ct[0] for ct in chart_types]}")
                
                for button_text, data_key in chart_types:
                    try:
                        app.logger.info(f"Looking for '{button_text}' button...")
                        
                        # Click the chart type button - try multiple selectors
                        chart_button = await self.page.query_selector(f'button.chart-type-btn:has-text("{button_text}")')
                        if not chart_button:
                            chart_button = await self.page.query_selector(f'button:has-text("{button_text}")')
                        if not chart_button:
                            # Try case-insensitive search
                            chart_button = await self.page.query_selector(f'button:has-text("{button_text.lower()}")')
                        
                        if chart_button:
                            try:
                                # Check if button is visible before clicking
                                is_visible = await chart_button.is_visible()
                                if is_visible:
                                    await chart_button.click()
                                    await asyncio.sleep(2)
                                    app.logger.info(f"Clicked '{button_text}' button")
                                else:
                                    app.logger.warning(f"Button '{button_text}' found but not visible")
                                    # Take a screenshot for debugging
                                    await self.page.screenshot(path=f'/tmp/srp_no_button_{data_key}.png')
                                    continue
                            except Exception as e:
                                app.logger.warning(f"Error clicking '{button_text}' button: {e}")
                                continue
                        
                        # Check if we need to switch to table view
                        is_table_view = await self.page.query_selector('table')
                        if not is_table_view:
                            # Try to find button to switch to table view
                            view_table_btn = await self.page.query_selector('button:has-text("View as table")')
                            if not view_table_btn:
                                view_table_btn = await self.page.query_selector('button:has-text("View data table")')
                        else:
                            # Already in table view
                            view_table_btn = None
                        
                        if view_table_btn:
                            await view_table_btn.click()
                            await asyncio.sleep(2)
                            
                            # Extract table data for this specific chart type
                            table_data = await self.page.evaluate("""
                                () => {
                                    const result = {
                                        headers: [],
                                        rows: []
                                    };
                                    
                                    // Find the table
                                    const table = document.querySelector('table');
                                    if (!table) return result;
                                    
                                    // Get headers
                                    const headerCells = table.querySelectorAll('thead th, thead td');
                                    headerCells.forEach(cell => {
                                        result.headers.push(cell.textContent.trim());
                                    });
                                    
                                    // Get rows
                                    const rows = table.querySelectorAll('tbody tr');
                                    rows.forEach(row => {
                                        const rowData = [];
                                        const cells = row.querySelectorAll('td');
                                        cells.forEach(cell => {
                                            rowData.push(cell.textContent.trim());
                                        });
                                        if (rowData.length > 0) {
                                            result.rows.push(rowData);
                                        }
                                    });
                                    
                                    return result;
                                }
                            """)
                            
                            app.logger.info(f"Table for {button_text}: {len(table_data.get('rows', []))} rows")
                            app.logger.info(f"Headers for {button_text}: {table_data.get('headers', [])}")
                            if table_data.get('rows'):
                                app.logger.info(f"First row for {button_text}: {table_data['rows'][0]}")
                            
                            # Parse the data based on chart type
                            if table_data.get('rows'):
                                if data_key == 'netEnergy':
                                    # Net energy table - look for the net/total column
                                    headers = table_data.get('headers', [])
                                    # Find the column with net or total kWh
                                    net_col = None
                                    for i, header in enumerate(headers):
                                        if 'net' in header.lower() or 'total' in header.lower():
                                            net_col = i
                                            break
                                    
                                    if net_col is None and len(headers) > 2:
                                        # Default to column 2 if no net/total column found
                                        net_col = 2
                                    
                                    for row in table_data['rows']:
                                        if len(row) > net_col:
                                            try:
                                                value_text = row[net_col]
                                                # Handle negative values in parentheses
                                                if '(' in value_text and ')' in value_text:
                                                    value_text = '-' + value_text.replace('(', '').replace(')', '')
                                                value = float(value_text.replace(',', '').replace(' kWh', '').replace('kWh', '').strip())
                                                chart_data['netEnergy'].append(value)
                                            except Exception as e:
                                                app.logger.warning(f"Error parsing net energy value: {e}, value_text: '{value_text}'")
                                
                                elif data_key == 'generation':
                                    # Generation data - look for generation or export column
                                    headers = table_data.get('headers', [])
                                    gen_col = None
                                    for i, header in enumerate(headers):
                                        if 'generation' in header.lower() or 'export' in header.lower() or 'total' in header.lower():
                                            gen_col = i
                                            break
                                    
                                    if gen_col is None and len(headers) > 2:
                                        gen_col = 2
                                    
                                    for row in table_data['rows']:
                                        if len(row) > gen_col:
                                            try:
                                                value_text = row[gen_col]
                                                if '(' in value_text and ')' in value_text:
                                                    value_text = '-' + value_text.replace('(', '').replace(')', '')
                                                value = float(value_text.replace(',', '').replace(' kWh', '').replace('kWh', '').strip())
                                                chart_data['generation'].append(value)
                                            except Exception as e:
                                                app.logger.warning(f"Error parsing generation value: {e}, value_text: '{value_text}'")
                                
                                elif data_key == 'usage':
                                    # Usage data - look for usage or consumption column
                                    headers = table_data.get('headers', [])
                                    usage_col = None
                                    for i, header in enumerate(headers):
                                        header_lower = header.lower()
                                        # Skip date columns
                                        if 'date' in header_lower:
                                            continue
                                        if 'total' in header_lower and 'kwh' in header_lower:
                                            usage_col = i
                                            break
                                        elif 'usage' in header_lower and 'kwh' in header_lower:
                                            usage_col = i
                                            break
                                    
                                    if usage_col is None and len(headers) > 2:
                                        usage_col = 2
                                    
                                    for row in table_data['rows']:
                                        if len(row) > usage_col:
                                            try:
                                                value_text = row[usage_col]
                                                if '(' in value_text and ')' in value_text:
                                                    value_text = '-' + value_text.replace('(', '').replace(')', '')
                                                value = float(value_text.replace(',', '').replace(' kWh', '').replace('kWh', '').strip())
                                                chart_data['usage'].append(value)
                                            except Exception as e:
                                                app.logger.warning(f"Error parsing usage value: {e}, value_text: '{value_text}'")
                                
                                elif data_key == 'demand':
                                    # Demand data in kW
                                    headers = table_data.get('headers', [])
                                    demand_col = None
                                    for i, header in enumerate(headers):
                                        if 'demand' in header.lower() or 'peak' in header.lower() or 'max' in header.lower():
                                            demand_col = i
                                            break
                                    
                                    if demand_col is None and len(headers) > 2:
                                        demand_col = 2
                                    
                                    for row in table_data['rows']:
                                        if len(row) > demand_col:
                                            try:
                                                value_text = row[demand_col]
                                                if '(' in value_text and ')' in value_text:
                                                    value_text = '-' + value_text.replace('(', '').replace(')', '')
                                                value = float(value_text.replace(',', '').replace(' kW', '').replace('kW', '').strip())
                                                chart_data['demand'].append(value)
                                            except Exception as e:
                                                app.logger.warning(f"Error parsing demand value: {e}, value_text: '{value_text}'")
                            
                            # Click back to chart view if needed
                            view_chart_btn = await self.page.query_selector('button:has-text("View as chart")')
                            if view_chart_btn:
                                await view_chart_btn.click()
                                await asyncio.sleep(1)
                            else:
                                # Try alternative button text
                                view_chart_btn = await self.page.query_selector('button:has-text("View chart")')
                                if view_chart_btn:
                                    await view_chart_btn.click()
                                    await asyncio.sleep(1)
                        else:
                            app.logger.warning(f"'{button_text}' button not found")
                            # Take a screenshot for debugging
                            await self.page.screenshot(path=f'/tmp/srp_no_button_{data_key}.png')
                    
                    except Exception as e:
                        app.logger.error(f"Error processing chart type {button_text}: {e}")
            
            # If we didn't find a date range, create one from the dates
            if not chart_data['dateRange'] and chart_data['dates']:
                chart_data['dateRange'] = f"{chart_data['dates'][0]} through {chart_data['dates'][-1]}"
            
            # Calculate missing data from off-peak and on-peak if needed
            if chart_data['offPeak'] and chart_data['onPeak']:
                # Calculate usage if not already populated
                if not chart_data['usage'] or all(v == 0 for v in chart_data['usage']):
                    chart_data['usage'] = []
                    for i in range(len(chart_data['offPeak'])):
                        # Usage is the sum of off-peak and on-peak (absolute values)
                        usage = abs(chart_data['offPeak'][i]) + abs(chart_data['onPeak'][i])
                        chart_data['usage'].append(usage)
                
                # Calculate net energy if not already populated
                if not chart_data['netEnergy'] or all(v == 0 for v in chart_data['netEnergy']):
                    chart_data['netEnergy'] = []
                    for i in range(len(chart_data['offPeak'])):
                        # Net energy is the sum (negative means net generation)
                        net = chart_data['offPeak'][i] + chart_data['onPeak'][i]
                        chart_data['netEnergy'].append(net)
                
                # Calculate generation if not already populated
                if not chart_data['generation'] or all(v == 0 for v in chart_data['generation']):
                    chart_data['generation'] = []
                    for i in range(len(chart_data['offPeak'])):
                        # Generation is the negative portion
                        off_gen = min(0, chart_data['offPeak'][i])
                        on_gen = min(0, chart_data['onPeak'][i])
                        generation = abs(off_gen + on_gen)
                        chart_data['generation'].append(generation)
            
            app.logger.info(f"SRP daily usage chart extracted: {len(chart_data.get('dates', []))} days")
            if chart_data.get('dates'):
                app.logger.info(f"SRP chart data extracted successfully")
                app.logger.info(f"Data counts - usage: {len(chart_data.get('usage', []))}, netEnergy: {len(chart_data.get('netEnergy', []))}, generation: {len(chart_data.get('generation', []))}")
            else:
                app.logger.warning("SRP chart data extraction returned empty data")
            
            return chart_data
            
        except Exception as e:
            print(f"Error getting daily usage chart: {e}")
            app.logger.error(f"Error getting daily usage chart: {e}")
            return {'error': str(e)}
    
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

class SRPWebMonitor:
    """Monitor for SRP (Salt River Project) usage data"""
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None
        self.base_url = 'https://myaccount.srpnet.com'
        
    async def start(self):
        """Start the browser with proper settings"""
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--single-process',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-blink-features=AutomationControlled'
        ]
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=browser_args
        )
        self.page = await self.browser.new_page()
        
    async def login(self, username, password):
        """Login to SRP account"""
        try:
            logger.info(f"SRP: Navigating to login page...")
            await self.page.goto('https://myaccount.srpnet.com', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Check if already logged in
            current_url = self.page.url
            logger.info(f"SRP: Current URL: {current_url}")
            if '/myaccount/dashboard' in current_url.lower() or 'power/myaccount/dashboard' in current_url.lower():
                logger.info("SRP: Already logged in")
                return True
                
            # Fill login form
            logger.info("SRP: Looking for username field...")
            try:
                username_field = await self.page.wait_for_selector('input[name="username"], input#username_desktop', timeout=5000)
            except:
                # Check again if we're on dashboard (sometimes redirect happens)
                await asyncio.sleep(2)
                current_url = self.page.url
                logger.info(f"SRP: Rechecking URL after wait: {current_url}")
                if '/myaccount/dashboard' in current_url.lower() or 'power/myaccount/dashboard' in current_url.lower():
                    logger.info("SRP: Login redirect completed - already logged in")
                    return True
                raise
            await username_field.fill(username)
            logger.info("SRP: Username filled")
            
            password_field = await self.page.query_selector('input[name="password"], input#password_desktop')
            if password_field:
                await password_field.fill(password)
                logger.info("SRP: Password filled")
                
            # Submit
            submit_btn = await self.page.query_selector('button[type="submit"], button:has-text("Sign In")')
            if submit_btn:
                logger.info("SRP: Clicking submit button...")
                await submit_btn.click()
                await self.page.wait_for_load_state('networkidle', timeout=15000)
            else:
                logger.warning("SRP: Submit button not found")
                
            # Verify login
            await asyncio.sleep(3)
            final_url = self.page.url
            logger.info(f"SRP: Final URL after login: {final_url}")
            success = 'myaccount/dashboard' in final_url.lower()
            logger.info(f"SRP: Login success check: {success} (looking for 'myaccount/dashboard' in '{final_url.lower()}')")
            return success
            
        except Exception as e:
            logger.error(f"SRP login error: {e}")
            return False
            
    async def navigate_to_usage(self):
        """Navigate to usage page"""
        try:
            logger.info("SRP: Navigating directly to usage page...")
            # Navigate directly to the usage page URL
            await self.page.goto(f"{self.base_url}/power/myaccount/usage", wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Click on the Daily tab to show the daily usage view
            logger.info("SRP: Looking for Daily tab...")
            daily_tab = await self.page.query_selector('button:has-text("Daily")')
            if not daily_tab:
                # Try alternative selectors
                daily_tab = await self.page.query_selector('.MuiTab-root:has-text("Daily")')
            
            if daily_tab:
                logger.info("SRP: Clicking Daily tab...")
                await daily_tab.click()
                await asyncio.sleep(2)
                
                # Click Submit button to load the daily data
                submit_button = await self.page.query_selector('button.btn.srp-btn.btn-green:has-text("Submit")')
                if submit_button:
                    logger.info("SRP: Clicking Submit button to load daily data...")
                    await submit_button.click()
                    await asyncio.sleep(3)
                    await self.page.wait_for_load_state('networkidle')
                else:
                    logger.info("SRP: Submit button not found, data might already be loaded")
                
                return True
            else:
                logger.warning("SRP: Daily tab not found")
                return False
                
        except Exception as e:
            logger.error(f"SRP navigation error: {e}")
            return False
            
    async def extract_usage_data(self):
        """Extract daily usage data"""
        try:
            logger.info("SRP: Extracting usage data...")
            # Switch to chart view
            chart_btn = await self.page.query_selector('button:has-text("View as chart")')
            if chart_btn:
                logger.info("SRP: Switching to chart view...")
                await chart_btn.click()
                await asyncio.sleep(2)
                
            # Extract data from table (fallback if chart parsing fails)
            usage_data = []
            
            # Try to find usage rows
            logger.info("SRP: Looking for usage rows...")
            rows = await self.page.query_selector_all('tr[class*="usage-row"], tr[data-date]')
            logger.info(f"SRP: Found {len(rows)} usage rows")
            
            for row in rows[-7:]:  # Last 7 days
                try:
                    date_elem = await row.query_selector('td:first-child')
                    date_text = await date_elem.inner_text() if date_elem else ''
                    
                    # Find off-peak and on-peak values
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 4:
                        off_peak_text = await cells[2].inner_text()  # Assuming off-peak is 3rd column
                        on_peak_text = await cells[3].inner_text()   # Assuming on-peak is 4th column
                        
                        off_peak_kwh = float(off_peak_text.replace('kWh', '').strip())
                        on_peak_kwh = float(on_peak_text.replace('kWh', '').strip())
                        
                        usage_data.append({
                            'date': date_text,
                            'off_peak_kwh': off_peak_kwh,
                            'on_peak_kwh': on_peak_kwh
                        })
                except:
                    continue
                    
            return {
                'daily_usage': usage_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"SRP data extraction error: {e}")
            return None
            
    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def monitor_loop():
    """Background monitoring loop"""
    global monitor_data, monitor_running, credentials_verified, srp_data
    
    logger.info("Monitor loop started")
    
    if not credentials_verified:
        logger.error("Credentials not verified, stopping monitor")
        monitor_data = {'error': 'Credentials not verified'}
        return
    
    monitor = EG4WebMonitor()
    await monitor.start()
    
    # Initialize SRP monitor if credentials exist
    srp_monitor = None
    srp_username = os.getenv('SRP_USERNAME', '').strip().strip("'\"")
    srp_password = os.getenv('SRP_PASSWORD', '').strip().strip("'\"")
    
    logger.info(f"SRP credentials check - username: {srp_username[:3] + '***' if srp_username else 'None'}, has_password: {bool(srp_password)}")
    
    if srp_username and srp_password:
        try:
            srp_monitor = SRPWebMonitor()
            await srp_monitor.start()
            logger.info(f"SRP monitor initialized for user: {srp_username[:3]}***")
        except Exception as e:
            logger.error(f"Failed to initialize SRP monitor: {e}")
    
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
                
                # Fetch SRP data if monitor is available (run less frequently - every 5 updates)
                update_count = getattr(monitor_loop, 'update_count', 0)
                monitor_loop.update_count = update_count + 1
                
                if srp_monitor and (update_count % 5 == 1 or not srp_data):
                    try:
                        logger.info("Fetching SRP data...")
                        if await srp_monitor.login(srp_username, srp_password):
                            logger.info("SRP login successful, navigating to usage...")
                            if await srp_monitor.navigate_to_usage():
                                logger.info("SRP navigation successful, extracting data...")
                                usage_data = await srp_monitor.extract_usage_data()
                                if usage_data:
                                    srp_data = usage_data
                                    socketio.emit('srp_update', usage_data)
                                    logger.info(f"SRP data update sent: {len(usage_data.get('daily_usage', []))} days")
                                else:
                                    logger.warning("No SRP usage data extracted")
                            else:
                                logger.error("SRP navigation to usage page failed")
                        else:
                            logger.error("SRP login failed")
                    except Exception as e:
                        logger.error(f"SRP update error: {e}")
            
            # Wait before next update (1 minute)
            for i in range(60):
                if not monitor_running:
                    break
                await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Monitor error: {e}")
        monitor_data = {'error': str(e)}
    finally:
        await monitor.close()
        if srp_monitor:
            await srp_monitor.close()

def run_monitor():
    """Run the monitor in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(monitor_loop())

def start_monitoring_if_needed():
    """Start monitoring if credentials are verified"""
    global monitor_thread, monitor_running
    
    logger.info(f"start_monitoring_if_needed called - credentials_verified: {credentials_verified}, monitor_running: {monitor_running}")
    
    if credentials_verified and not monitor_running:
        monitor_running = True
        monitor_thread = threading.Thread(target=run_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        logger.info("Auto-started monitoring thread")

@app.route('/')
def index():
    """Main page with tabs"""
    return render_template('index_solar_style.html')

@app.route('/test')
def test_page():
    """Debug test page"""
    return render_template('test_page.html')

@app.route('/debug')
def debug_page():
    """Simple debug page"""
    return render_template('debug.html')

@app.route('/api/debug')
def debug_endpoint():
    """Debug endpoint to check system status"""
    try:
        global monitor_task
        debug_info = {
            'monitor_running': monitor_task is not None and not monitor_task.done() if monitor_task else False,
            'connected_clients': len(connected_clients),
            'last_data': {
                'soc': battery_soc,
                'power': battery_power,
                'pv': pv_power,
                'grid': grid_power,
                'load': load_power,
                'timestamp': datetime.now().isoformat()
            },
            'credentials_status': {
                'eg4_username': eg4_username is not None,
                'eg4_password': eg4_password is not None,
                'srp_username': srp_username is not None,
                'srp_password': srp_password is not None
            }
        }
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            logger.info(f"Verifying credentials for user: {username}")
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

@app.route('/api/config/delete-eg4', methods=['POST'])
def delete_eg4_credentials():
    """Delete EG4 credentials from .env file"""
    global credentials_verified, monitor_running
    
    try:
        env_path = Path('.env')
        env_content = {}
        
        # Read existing content
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        # Skip EG4 credentials
                        if key not in ['EG4_MONITOR_USERNAME', 'EG4_MONITOR_PASSWORD', 'EG4_USERNAME', 'EG4_PASSWORD']:
                            env_content[key] = value
        
        # Write back without EG4 credentials
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        # Clear from environment
        os.environ.pop('EG4_MONITOR_USERNAME', None)
        os.environ.pop('EG4_MONITOR_PASSWORD', None)
        os.environ.pop('EG4_USERNAME', None)
        os.environ.pop('EG4_PASSWORD', None)
        
        # Stop monitoring
        credentials_verified = False
        monitor_running = False
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting EG4 credentials: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config/delete-srp', methods=['POST'])
def delete_srp_credentials():
    """Delete SRP credentials from .env file"""
    try:
        env_path = Path('.env')
        env_content = {}
        
        # Read existing content
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        # Skip SRP credentials
                        if key not in ['SRP_USERNAME', 'SRP_PASSWORD']:
                            env_content[key] = value
        
        # Write back without SRP credentials
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        # Clear from environment
        os.environ.pop('SRP_USERNAME', None)
        os.environ.pop('SRP_PASSWORD', None)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting SRP credentials: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/srp/demand', methods=['GET'])
def get_srp_demand():
    """Get SRP peak demand data with caching"""
    global srp_cache
    
    # Check if we have valid cached data
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    if not force_refresh and srp_cache['data'] and srp_cache['timestamp']:
        # Check if we should use cached data based on the demand date
        cache_age = datetime.now() - srp_cache['timestamp']
        demand_date_str = srp_cache['data'].get('demandDate', '')
        
        # Parse the demand date
        if demand_date_str:
            try:
                # Handle YYYY-MM-DD format
                if '-' in demand_date_str and len(demand_date_str) == 10:
                    demand_date = datetime.strptime(demand_date_str, '%Y-%m-%d').date()
                else:
                    # Handle other formats - assume current year
                    demand_date = datetime.strptime(f"{demand_date_str} {datetime.now().year}", '%b %d %Y').date()
            except:
                demand_date = datetime.now().date()
        else:
            demand_date = datetime.now().date()
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # If demand date is yesterday or today, cache is valid
        if demand_date >= yesterday:
            print(f"Returning cached SRP data from {srp_cache['timestamp']} (demand date: {demand_date})")
            cached_data = srp_cache['data'].copy()
            cached_data['cached'] = True
            cached_data['cache_timestamp'] = srp_cache['timestamp'].isoformat()
            cached_data['cache_age_seconds'] = int(cache_age.total_seconds())
            return jsonify(cached_data)
        # If demand date is older, only use cache if less than 1 hour old
        elif cache_age.total_seconds() < 3600:  # 1 hour
            print(f"Returning cached SRP data (old demand date {demand_date}, but cache is fresh)")
            cached_data = srp_cache['data'].copy()
            cached_data['cached'] = True
            cached_data['cache_timestamp'] = srp_cache['timestamp'].isoformat()
            cached_data['cache_age_seconds'] = int(cache_age.total_seconds())
            cached_data['stale_demand'] = True
            return jsonify(cached_data)
        else:
            print(f"Cache expired - demand date {demand_date} is old and cache is > 1 hour")
    
    # Check if credentials exist
    username = os.getenv('SRP_USERNAME', '').strip().strip("'\"")
    password = os.getenv('SRP_PASSWORD', '').strip().strip("'\"")
    
    if not username or not password:
        return jsonify({'error': 'no_credentials', 'message': 'SRP credentials not configured'}), 401
    
    # Fetch fresh data
    async def fetch_srp_data():
        srp = SRPMonitor()
        try:
            await srp.start()
            if await srp.login():
                demand_data = await srp.get_peak_demand()
                # Cache the successful result
                if demand_data and 'error' not in demand_data:
                    srp_cache['data'] = demand_data
                    srp_cache['timestamp'] = datetime.now()
                    demand_data['cached'] = False
                    demand_data['cache_timestamp'] = srp_cache['timestamp'].isoformat()
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

@app.route('/api/srp/chart', methods=['GET'])
def get_srp_chart():
    """Get SRP daily usage chart data with caching"""
    global srp_chart_cache
    
    # Check if credentials exist
    username = os.getenv('SRP_USERNAME', '').strip().strip("'\"")
    password = os.getenv('SRP_PASSWORD', '').strip().strip("'\"")
    
    if not username or not password:
        return jsonify({'error': 'no_credentials', 'message': 'SRP credentials not configured'}), 401
    
    # Check if we have valid cached data
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    if not force_refresh and srp_chart_cache['data'] and srp_chart_cache['timestamp']:
        cache_age = datetime.now() - srp_chart_cache['timestamp']
        # Cache chart data for 6 hours
        if cache_age.total_seconds() < 21600:
            print(f"Returning cached SRP chart data from {srp_chart_cache['timestamp']}")
            cached_data = srp_chart_cache['data'].copy()
            cached_data['cached'] = True
            cached_data['cache_age_seconds'] = int(cache_age.total_seconds())
            cached_data['cache_timestamp'] = srp_chart_cache['timestamp'].isoformat()
            return jsonify(cached_data)
    
    # Fetch chart data
    async def fetch_chart_data():
        # Add a small delay to avoid conflicts with other SRP requests
        await asyncio.sleep(2)
        
        srp = SRPMonitor()
        try:
            await srp.start()
            # Add retry logic for login
            login_attempts = 0
            login_success = False
            
            while login_attempts < 3 and not login_success:
                login_attempts += 1
                print(f"SRP chart login attempt {login_attempts}/3")
                
                try:
                    login_success = await srp.login()
                    if not login_success and login_attempts < 3:
                        print(f"Login attempt {login_attempts} failed, retrying...")
                        await asyncio.sleep(5)
                except Exception as e:
                    print(f"Login attempt {login_attempts} error: {e}")
                    if login_attempts < 3:
                        await asyncio.sleep(5)
            
            if login_success:
                chart_data = await srp.get_daily_usage_chart()
                return chart_data
            else:
                return {'error': 'Failed to login to SRP after 3 attempts'}
        except Exception as e:
            return {'error': str(e)}
        finally:
            await srp.close()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(fetch_chart_data())
    
    # Process the result to add combined usage data
    if result and not result.get('error'):
        # Calculate usage as sum of all rate periods
        if 'rateBreakdown' in result:
            usage = []
            num_days = len(result.get('dates', []))
            
            for i in range(num_days):
                daily_usage = 0
                for rate_type in ['offPeak', 'onPeak', 'superOffPeak']:
                    if rate_type in result['rateBreakdown'] and i < len(result['rateBreakdown'][rate_type]):
                        daily_usage += result['rateBreakdown'][rate_type][i]
                usage.append(daily_usage)
            
            result['usage'] = usage
        
        # Cache successful result
        srp_chart_cache['data'] = result
        srp_chart_cache['timestamp'] = datetime.now()
        print(f"SRP chart data cached at {srp_chart_cache['timestamp']}")
    
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
    logger.info(f"Client connected from {request.remote_addr}")
    
    # Check monitoring status
    if not credentials_verified:
        emit('status', {'message': 'Please configure EG4 credentials', 'type': 'warning'})
    elif not monitor_running:
        emit('status', {'message': 'Monitoring will start shortly...', 'type': 'info'})
        # Don't start monitor here - let it start from the main startup
    
    # Send current data if available
    if monitor_data and 'error' not in monitor_data:
        emit('monitor_update', monitor_data)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

if __name__ == '__main__':
    # Check if credentials exist
    username = os.getenv('EG4_MONITOR_USERNAME', '').strip().strip("'\"")
    password = os.getenv('EG4_MONITOR_PASSWORD', '').strip().strip("'\"")
    
    if username and password:
        # Verify existing credentials
        logger.info("Verifying existing credentials...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        credentials_verified = loop.run_until_complete(verify_credentials_async(username, password))
        
        if credentials_verified:
            logger.info("Existing credentials verified!")
            logger.info(f"About to call start_monitoring_if_needed - monitor_running={monitor_running}")
            start_monitoring_if_needed()
            logger.info("Monitoring thread startup initiated")
        else:
            logger.warning("Existing credentials could not be verified")
    else:
        logger.warning("No EG4 credentials found in environment")
    
    # Run the application
    logger.info(f"Starting Flask application on http://0.0.0.0:8282")
    socketio.run(app, host='0.0.0.0', port=8282, debug=False, allow_unsafe_werkzeug=True)