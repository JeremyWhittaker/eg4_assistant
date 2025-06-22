#!/usr/bin/env python3
"""
EG4 Real-time Cloud Monitor - Displays live data from EG4 cloud
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class EG4RealtimeCloudMonitor:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.browser = None
        self.page = None
        
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
    
    async def navigate_to_monitor(self):
        """Navigate to the monitor page"""
        await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
        
        # Wait for data to load
        for i in range(30):
            await asyncio.sleep(1)
            soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
            if soc and soc != '--':
                return True
        
        return False
    
    async def extract_data(self):
        """Extract all available data from the page"""
        try:
            stats = await self.page.evaluate("""
                () => {
                    let data = {};
                    
                    // Helper function to clean text
                    const cleanText = (text) => {
                        if (!text || text === '--' || text === '') return '--';
                        return text.trim();
                    };
                    
                    // Battery data
                    data.battery = {
                        power: cleanText(document.querySelector('.batteryPowerText')?.textContent),
                        soc: cleanText(document.querySelector('.socText')?.textContent),
                        voltage: cleanText(document.querySelector('.vbatText')?.textContent),
                        current: cleanText(document.querySelector('.batteryCurrentText')?.textContent)
                    };
                    
                    // PV data
                    data.pv = {
                        pv1_power: cleanText(document.querySelector('.pv1PowerText')?.textContent),
                        pv1_voltage: cleanText(document.querySelector('.vpv1Text')?.textContent),
                        pv1_current: cleanText(document.querySelector('.ipv1Text')?.textContent),
                        pv2_power: cleanText(document.querySelector('.pv2PowerText')?.textContent),
                        pv2_voltage: cleanText(document.querySelector('.vpv2Text')?.textContent),
                        pv2_current: cleanText(document.querySelector('.ipv2Text')?.textContent),
                        total_power: cleanText(document.querySelector('.pvPowerText')?.textContent)
                    };
                    
                    // Grid data
                    data.grid = {
                        power: cleanText(document.querySelector('.gridPowerText')?.textContent),
                        voltage: cleanText(document.querySelector('.vacText')?.textContent),
                        frequency: cleanText(document.querySelector('.facText')?.textContent),
                        current: cleanText(document.querySelector('.igridText')?.textContent)
                    };
                    
                    // Load data
                    data.load = {
                        power: cleanText(document.querySelector('.consumptionPowerText')?.textContent),
                        percentage: cleanText(document.querySelector('.loadPercentText')?.textContent),
                        current: cleanText(document.querySelector('.iloadText')?.textContent)
                    };
                    
                    // Daily statistics
                    data.daily = {
                        yield: cleanText(document.querySelector('#todayYieldingText')?.textContent),
                        consumption: cleanText(document.querySelector('#todayConsumptionText')?.textContent),
                        grid_import: cleanText(document.querySelector('#todayImportText')?.textContent),
                        grid_export: cleanText(document.querySelector('#todayExportText')?.textContent),
                        battery_charge: cleanText(document.querySelector('#todayChargeText')?.textContent),
                        battery_discharge: cleanText(document.querySelector('#todayDischargeText')?.textContent)
                    };
                    
                    // Total statistics
                    data.total = {
                        yield: cleanText(document.querySelector('#totalYieldingText')?.textContent),
                        consumption: cleanText(document.querySelector('#totalConsumptionText')?.textContent),
                        grid_import: cleanText(document.querySelector('#totalImportText')?.textContent),
                        grid_export: cleanText(document.querySelector('#totalExportText')?.textContent)
                    };
                    
                    // Additional info
                    data.info = {
                        status: cleanText(document.querySelector('.statusText')?.textContent),
                        temperature: cleanText(document.querySelector('.tempText')?.textContent)
                    };
                    
                    return data;
                }
            """)
            
            return stats
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            return None
    
    def display_data(self, stats):
        """Display the extracted data"""
        if not stats:
            print("No data available")
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Clear screen for clean display
        print("\033[2J\033[H")  # Clear screen and move cursor to top
        
        print(f"{'='*70}")
        print(f"EG4 REAL-TIME MONITOR - {timestamp}")
        print(f"{'='*70}")
        
        # Battery Section with visual bar
        print(f"\n🔋 BATTERY")
        soc = stats['battery']['soc']
        power = stats['battery']['power']
        
        if soc != '--':
            try:
                soc_val = int(soc.replace('%', ''))
                bar_length = 30
                filled = int(bar_length * soc_val / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                # Determine charging/discharging status
                if power != '--':
                    power_val = int(power.replace('W', '').strip())
                    if power_val > 0:
                        status = "↑ CHARGING"
                        color = "\033[92m"  # Green
                    elif power_val < 0:
                        status = "↓ DISCHARGING"
                        color = "\033[91m"  # Red
                    else:
                        status = "= IDLE"
                        color = "\033[93m"  # Yellow
                else:
                    status = ""
                    color = ""
                
                print(f"  [{color}{bar}\033[0m] {soc}% {status}")
            except:
                print(f"  SOC: {soc}%")
        
        print(f"  Power:   {power} W")
        print(f"  Voltage: {stats['battery']['voltage']} V")
        print(f"  Current: {stats['battery']['current']} A")
        
        # PV Section
        print(f"\n☀️  SOLAR")
        pv1 = stats['pv']['pv1_power']
        pv2 = stats['pv']['pv2_power']
        total = stats['pv']['total_power']
        
        print(f"  PV1: {pv1:>8} W  ({stats['pv']['pv1_voltage']} V, {stats['pv']['pv1_current']} A)")
        print(f"  PV2: {pv2:>8} W  ({stats['pv']['pv2_voltage']} V, {stats['pv']['pv2_current']} A)")
        print(f"  {'─'*35}")
        print(f"  Total: {total:>6} W")
        
        # Power Flow Diagram
        print(f"\n⚡ POWER FLOW")
        print(f"  Solar → {stats['pv']['total_power']:>6} W")
        print(f"  Grid  → {stats['grid']['power']:>6} W ({stats['grid']['voltage']} V @ {stats['grid']['frequency']} Hz)")
        print(f"  Load  ← {stats['load']['power']:>6} W ({stats['load']['percentage']}% of capacity)")
        
        # Daily Statistics
        print(f"\n📊 TODAY")
        print(f"  Generated:  {stats['daily']['yield']:>8} kWh")
        print(f"  Consumed:   {stats['daily']['consumption']:>8} kWh")
        print(f"  From Grid:  {stats['daily']['grid_import']:>8} kWh")
        print(f"  To Grid:    {stats['daily']['grid_export']:>8} kWh")
        print(f"  Bat Charge: {stats['daily']['battery_charge']:>8} kWh")
        print(f"  Bat Disch:  {stats['daily']['battery_discharge']:>8} kWh")
        
        # Lifetime Statistics
        print(f"\n📈 LIFETIME")
        print(f"  Total Generated: {stats['total']['yield']} kWh")
        print(f"  Total Consumed:  {stats['total']['consumption']} kWh")
        print(f"  Total Imported:  {stats['total']['grid_import']} kWh")
        print(f"  Total Exported:  {stats['total']['grid_export']} kWh")
        
        # System Status
        if stats['info']['status'] or stats['info']['temperature']:
            print(f"\n⚙️  SYSTEM")
            if stats['info']['status']:
                print(f"  Status: {stats['info']['status']}")
            if stats['info']['temperature']:
                print(f"  Temperature: {stats['info']['temperature']}")
        
        print(f"\n{'='*70}")
        print("Press Ctrl+C to exit | Updates every 30 seconds")
    
    async def run_monitor(self):
        """Run the monitoring loop"""
        try:
            print("Starting EG4 Cloud Monitor...")
            
            if not await self.login():
                print("Login failed!")
                return
                
            print("Login successful! Loading monitor page...")
            
            if not await self.navigate_to_monitor():
                print("Failed to load data. Inverter may be offline.")
                return
            
            print("\nConnected! Starting real-time monitoring...")
            await asyncio.sleep(1)
            
            while True:
                stats = await self.extract_data()
                self.display_data(stats)
                
                # Reload page every 5 minutes to ensure fresh data
                if hasattr(self, '_loop_count'):
                    self._loop_count += 1
                    if self._loop_count >= 10:  # 10 * 30s = 5 minutes
                        await self.page.reload(wait_until='networkidle')
                        await asyncio.sleep(2)
                        self._loop_count = 0
                else:
                    self._loop_count = 0
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
        except KeyboardInterrupt:
            print("\n\nShutting down monitor...")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            await self.close()
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()

async def main():
    """Main function"""
    monitor = EG4RealtimeCloudMonitor()
    await monitor.start()
    await monitor.run_monitor()

if __name__ == "__main__":
    asyncio.run(main())