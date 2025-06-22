#!/usr/bin/env python3
"""
EG4 Working Cloud Monitor - Waits for data to load properly
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv
import time

load_dotenv()

class EG4WorkingCloudMonitor:
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
        context = await self.browser.new_context()
        self.page = await context.new_page()
        
        # Enable console logging for debugging
        self.page.on("console", lambda msg: print(f"Console: {msg.text}") if "error" in msg.text.lower() else None)
        
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
    
    async def wait_for_data_load(self):
        """Wait for real data to load on the page"""
        max_attempts = 20
        attempt = 0
        
        while attempt < max_attempts:
            # Check if SOC has real data (not '--')
            soc_text = await self.page.evaluate("() => document.querySelector('.socText')?.textContent || '--'")
            
            if soc_text != '--' and soc_text != '':
                print(f"Data loaded! SOC: {soc_text}%")
                return True
            
            # Check if there are any loading indicators
            loading_count = await self.page.evaluate("""
                () => {
                    const loadingElements = document.querySelectorAll('.loading:visible, .spinner:visible, [class*="loading"]:visible');
                    return Array.from(loadingElements).filter(el => el.offsetParent !== null).length;
                }
            """)
            
            if loading_count > 0:
                print(f"Waiting for {loading_count} loading elements...")
            
            attempt += 1
            await asyncio.sleep(1)
        
        print("Warning: Data did not load after maximum attempts")
        return False
    
    async def navigate_to_monitor(self):
        """Navigate to the monitor page and ensure data loads"""
        try:
            # First, go to the main monitor page
            await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
            
            # Wait for initial page load
            await asyncio.sleep(2)
            
            # Check if inverter is already selected by looking at the combogrid
            inverter_id = await self.page.evaluate("""
                () => {
                    const input = document.querySelector('#inverterSearchInput');
                    if (input) {
                        const hiddenInput = input.parentElement.querySelector('input[type="hidden"]');
                        return hiddenInput?.value || null;
                    }
                    return null;
                }
            """)
            
            if inverter_id:
                print(f"Inverter already selected: {inverter_id}")
            else:
                print("No inverter selected, may need manual selection")
            
            # Wait for data to load
            await self.wait_for_data_load()
            
            # Additional wait to ensure all data is loaded
            await asyncio.sleep(3)
            
            return True
            
        except Exception as e:
            print(f"Navigation error: {e}")
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
                        current: cleanText(document.querySelector('.batteryCurrentText')?.textContent),
                        maxChargeCurrent: cleanText(document.querySelector('.maxChgCurrText')?.textContent),
                        maxDischargeCurrent: cleanText(document.querySelector('.maxDischgCurrText')?.textContent)
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
                    
                    // Inverter status
                    data.inverter = {
                        status: cleanText(document.querySelector('.statusText')?.textContent),
                        temperature: cleanText(document.querySelector('.tempText')?.textContent),
                        model: cleanText(document.querySelector('.modelText')?.textContent)
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
        print(f"EG4 CLOUD MONITOR - {timestamp}")
        print(f"{'='*70}")
        
        # Battery Section
        print(f"\n🔋 BATTERY STATUS")
        soc = stats['battery']['soc']
        if soc != '--':
            try:
                soc_val = int(soc.replace('%', ''))
                bar_length = 30
                filled = int(bar_length * soc_val / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"  SOC:     [{bar}] {soc}%")
            except:
                print(f"  SOC:     {soc}%")
        else:
            print(f"  SOC:     {soc}")
            
        print(f"  Power:   {stats['battery']['power']} W")
        print(f"  Voltage: {stats['battery']['voltage']} V")
        print(f"  Current: {stats['battery']['current']} A")
        
        # PV Section
        print(f"\n☀️  SOLAR PANELS")
        print(f"  PV1:     {stats['pv']['pv1_power']} W ({stats['pv']['pv1_voltage']} V, {stats['pv']['pv1_current']} A)")
        print(f"  PV2:     {stats['pv']['pv2_power']} W ({stats['pv']['pv2_voltage']} V, {stats['pv']['pv2_current']} A)")
        print(f"  Total:   {stats['pv']['total_power']} W")
        
        # Grid Section
        print(f"\n⚡ GRID")
        print(f"  Power:   {stats['grid']['power']} W")
        print(f"  Voltage: {stats['grid']['voltage']} V")
        print(f"  Freq:    {stats['grid']['frequency']} Hz")
        print(f"  Current: {stats['grid']['current']} A")
        
        # Load Section
        print(f"\n🏠 LOAD")
        print(f"  Power:   {stats['load']['power']} W")
        print(f"  Usage:   {stats['load']['percentage']}%")
        print(f"  Current: {stats['load']['current']} A")
        
        # Inverter Status
        print(f"\n⚙️  INVERTER")
        print(f"  Status:  {stats['inverter']['status']}")
        print(f"  Temp:    {stats['inverter']['temperature']}")
        
        # Daily Statistics
        print(f"\n📊 TODAY'S STATISTICS")
        print(f"  Solar Yield:      {stats['daily']['yield']} kWh")
        print(f"  Consumption:      {stats['daily']['consumption']} kWh")
        print(f"  Grid Import:      {stats['daily']['grid_import']} kWh")
        print(f"  Grid Export:      {stats['daily']['grid_export']} kWh")
        print(f"  Battery Charge:   {stats['daily']['battery_charge']} kWh")
        print(f"  Battery Discharge:{stats['daily']['battery_discharge']} kWh")
        
        # Total Statistics
        print(f"\n📈 TOTAL STATISTICS")
        print(f"  Total Yield:      {stats['total']['yield']} kWh")
        print(f"  Total Consumption:{stats['total']['consumption']} kWh")
        print(f"  Total Import:     {stats['total']['grid_import']} kWh")
        print(f"  Total Export:     {stats['total']['grid_export']} kWh")
        
        print(f"\n{'='*70}")
        
        # Check if we have real data
        has_data = any(
            stats[cat][key] != '--' 
            for cat in ['battery', 'pv', 'grid', 'load'] 
            for key in stats[cat] 
            if key in stats[cat]
        )
        
        if not has_data:
            print("\n⚠️  WARNING: No real-time data available. Inverter may be offline.")
        
    async def run_monitor(self):
        """Run the monitoring loop"""
        try:
            if not await self.login():
                print("Login failed!")
                return
                
            print("Login successful! Loading monitor page...")
            
            if not await self.navigate_to_monitor():
                print("Failed to navigate to monitor page")
                return
            
            print("\nStarting real-time monitoring...")
            print("Press Ctrl+C to exit\n")
            
            while True:
                stats = await self.extract_data()
                self.display_data(stats)
                await asyncio.sleep(30)  # Update every 30 seconds
                
        except KeyboardInterrupt:
            print("\n\nExiting monitor...")
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
    monitor = EG4WorkingCloudMonitor()
    await monitor.start()
    await monitor.run_monitor()

if __name__ == "__main__":
    asyncio.run(main())