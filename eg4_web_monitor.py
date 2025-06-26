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
            
            # Now click "View as data table" to get the table view
            view_table_button = await self.page.query_selector('button:has-text("View as data table")')
            if not view_table_button:
                view_table_button = await self.page.query_selector('button:has-text("View data table")')
            
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
                
                # Click back to chart view
                view_chart_button = await self.page.query_selector('button:has-text("View as chart")')
                if view_chart_button:
                    await view_chart_button.click()
                    await asyncio.sleep(1)
            else:
                app.logger.warning("'View as data table' button not found")
            
            # Skip clicking through chart types if we already have the data
            if chart_data['offPeak'] and chart_data['onPeak'] and len(chart_data['offPeak']) > 0:
                app.logger.info("Data already extracted from initial table, skipping chart type buttons")
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
                            await chart_button.click()
                            await asyncio.sleep(2)
                            app.logger.info(f"Clicked '{button_text}' button")
                        
                        # Click "View as data table" for this chart type
                        view_table_btn = await self.page.query_selector('button:has-text("View as data table")')
                        if not view_table_btn:
                            view_table_btn = await self.page.query_selector('button:has-text("View data table")')
                        
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
                            
                            # Click back to chart view
                            view_chart_btn = await self.page.query_selector('button:has-text("View as chart")')
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