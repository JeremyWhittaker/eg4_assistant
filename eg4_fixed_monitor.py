#!/usr/bin/env python3
"""
EG4 Fixed Monitor - Properly selects inverter and extracts data
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class EG4FixedMonitor:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.browser = None
        self.page = None
        self.inverter_id = None
        
    async def start(self):
        """Start the browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        
    async def login(self):
        """Login to EG4 cloud monitor"""
        try:
            await self.page.goto(f"{self.base_url}/WManage/web/login", wait_until='networkidle')
            await self.page.wait_for_selector('input[name="account"]', timeout=10000)
            
            await self.page.fill('input[name="account"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            
            await self.page.wait_for_load_state('networkidle')
            
            return 'login' not in self.page.url
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def get_inverter_list(self):
        """Get list of available inverters"""
        try:
            # Navigate to the inverter list API endpoint
            response = await self.page.request.get(f"{self.base_url}/WManage/web/config/inverter/list")
            data = await response.json()
            
            if data and 'rows' in data:
                inverters = data['rows']
                if inverters:
                    print(f"Found {len(inverters)} inverter(s):")
                    for inv in inverters:
                        print(f"  ID: {inv.get('id')}, SN: {inv.get('serialNum')}, Name: {inv.get('alias', 'N/A')}")
                    return inverters[0]['id']  # Return first inverter ID
            return None
        except Exception as e:
            print(f"Error getting inverter list: {e}")
            return None
    
    async def get_realtime_data(self, inverter_id):
        """Get realtime data for specific inverter"""
        try:
            # First navigate to the monitor page with the inverter ID
            await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
            
            # Wait for page to fully load
            await asyncio.sleep(3)
            
            # Try to get data via API endpoint
            response = await self.page.request.post(
                f"{self.base_url}/WManage/web/monitor/inverter/getRealtimeData",
                data={'inverterId': str(inverter_id)}
            )
            
            if response.ok:
                data = await response.json()
                return data
            else:
                print(f"Failed to get realtime data: {response.status}")
                return None
                
        except Exception as e:
            print(f"Error getting realtime data: {e}")
            return None
    
    async def extract_data(self):
        """Extract all available data"""
        try:
            # Get inverter ID
            if not self.inverter_id:
                self.inverter_id = await self.get_inverter_list()
                if not self.inverter_id:
                    print("No inverters found!")
                    return None
            
            print(f"\nUsing inverter ID: {self.inverter_id}")
            
            # Get realtime data
            data = await self.get_realtime_data(self.inverter_id)
            
            if data:
                return self.parse_realtime_data(data)
            
            # If API didn't work, try page scraping with inverter ID in URL
            await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter?inverterId={self.inverter_id}", wait_until='networkidle')
            await asyncio.sleep(5)
            
            # Extract data from page
            stats = await self.page.evaluate("""
                () => {
                    let data = {};
                    
                    // Battery data
                    data.battery = {
                        power: document.querySelector('.batteryPowerText')?.textContent || '--',
                        soc: document.querySelector('.socText')?.textContent || '--',
                        voltage: document.querySelector('.vbatText')?.textContent || '--',
                        current: document.querySelector('.batteryCurrentText')?.textContent || '--'
                    };
                    
                    // PV data
                    data.pv = {
                        pv1_power: document.querySelector('.pv1PowerText')?.textContent || '--',
                        pv2_power: document.querySelector('.pv2PowerText')?.textContent || '--',
                        total_power: document.querySelector('.pvPowerText')?.textContent || '--'
                    };
                    
                    // Grid data
                    data.grid = {
                        power: document.querySelector('.gridPowerText')?.textContent || '--',
                        voltage: document.querySelector('.vacText')?.textContent || '--',
                        frequency: document.querySelector('.facText')?.textContent || '--'
                    };
                    
                    // Load data
                    data.load = {
                        power: document.querySelector('.consumptionPowerText')?.textContent || '--',
                        percentage: document.querySelector('.loadPercentText')?.textContent || '--'
                    };
                    
                    // Daily statistics
                    data.daily = {
                        yield: document.querySelector('#todayYieldingText')?.textContent || '--',
                        consumption: document.querySelector('#todayConsumptionText')?.textContent || '--',
                        grid_import: document.querySelector('#todayImportText')?.textContent || '--',
                        grid_export: document.querySelector('#todayExportText')?.textContent || '--'
                    };
                    
                    return data;
                }
            """)
            
            return stats
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            return None
    
    def parse_realtime_data(self, data):
        """Parse realtime data from API response"""
        try:
            stats = {
                'battery': {
                    'power': str(data.get('batteryPower', '--')),
                    'soc': str(data.get('soc', '--')),
                    'voltage': str(data.get('vBat', '--')),
                    'current': str(data.get('iBat', '--'))
                },
                'pv': {
                    'pv1_power': str(data.get('ppv1', '--')),
                    'pv2_power': str(data.get('ppv2', '--')),
                    'total_power': str(data.get('ppv', '--'))
                },
                'grid': {
                    'power': str(data.get('pgrid', '--')),
                    'voltage': str(data.get('vac', '--')),
                    'frequency': str(data.get('fac', '--'))
                },
                'load': {
                    'power': str(data.get('pload', '--')),
                    'percentage': str(data.get('loadPercent', '--'))
                },
                'daily': {
                    'yield': str(data.get('etoday', '--')),
                    'consumption': str(data.get('consumptionToday', '--')),
                    'grid_import': str(data.get('importToday', '--')),
                    'grid_export': str(data.get('exportToday', '--'))
                }
            }
            return stats
        except Exception as e:
            print(f"Error parsing data: {e}")
            return None
    
    def display_data(self, stats):
        """Display the extracted data"""
        if not stats:
            print("No data available")
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{'='*60}")
        print(f"EG4 Monitor - {timestamp}")
        print(f"{'='*60}")
        
        # Battery Section
        print(f"\n🔋 BATTERY STATUS")
        print(f"  SOC:     {stats['battery']['soc']}%")
        print(f"  Power:   {stats['battery']['power']} W")
        print(f"  Voltage: {stats['battery']['voltage']} V")
        print(f"  Current: {stats['battery']['current']} A")
        
        # PV Section
        print(f"\n☀️  SOLAR PANELS")
        print(f"  PV1:     {stats['pv']['pv1_power']} W")
        print(f"  PV2:     {stats['pv']['pv2_power']} W")
        print(f"  Total:   {stats['pv']['total_power']} W")
        
        # Grid Section
        print(f"\n⚡ GRID")
        print(f"  Power:   {stats['grid']['power']} W")
        print(f"  Voltage: {stats['grid']['voltage']} V")
        print(f"  Freq:    {stats['grid']['frequency']} Hz")
        
        # Load Section
        print(f"\n🏠 LOAD")
        print(f"  Power:   {stats['load']['power']} W")
        print(f"  Usage:   {stats['load']['percentage']}%")
        
        # Daily Statistics
        print(f"\n📊 TODAY'S STATISTICS")
        print(f"  Yield:       {stats['daily']['yield']} kWh")
        print(f"  Consumption: {stats['daily']['consumption']} kWh")
        print(f"  Grid Import: {stats['daily']['grid_import']} kWh")
        print(f"  Grid Export: {stats['daily']['grid_export']} kWh")
        
        print(f"\n{'='*60}\n")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()

async def main():
    """Main function"""
    monitor = EG4FixedMonitor()
    await monitor.start()
    
    try:
        print("Logging in...")
        if await monitor.login():
            print("Login successful!")
            
            while True:
                stats = await monitor.extract_data()
                monitor.display_data(stats)
                
                print("Press Ctrl+C to exit")
                await asyncio.sleep(30)  # Update every 30 seconds
        else:
            print("Login failed!")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        await monitor.close()

if __name__ == "__main__":
    asyncio.run(main())