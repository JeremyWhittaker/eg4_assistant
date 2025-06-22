#!/usr/bin/env python3
"""
EG4 Live Dashboard - Compact real-time display of key metrics
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class EG4LiveDashboard:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.browser = None
        self.page = None
        
    async def start(self, headless=True):
        """Start the browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
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
    
    async def get_live_data(self):
        """Get essential live data"""
        try:
            if '/monitor/inverter' not in self.page.url:
                await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
                await asyncio.sleep(2)
            
            # Extract key metrics
            data = await self.page.evaluate("""
                () => {
                    // Helper function to parse numeric values
                    const parseValue = (selector) => {
                        const elem = document.querySelector(selector);
                        if (!elem) return null;
                        const text = elem.textContent.trim();
                        const num = parseFloat(text.replace(/,/g, ''));
                        return isNaN(num) ? text : num;
                    };
                    
                    return {
                        // Power flows
                        pv_total: (parseValue('.pv1PowerText') || 0) + 
                                 (parseValue('.pv2PowerText') || 0) + 
                                 (parseValue('.pv3PowerText') || 0),
                        battery_power: parseValue('.batteryPowerText'),
                        grid_power: parseValue('.gridPowerText'),
                        load_power: parseValue('.consumptionPowerText'),
                        
                        // Battery status
                        battery_soc: parseValue('.socText'),
                        battery_voltage: parseValue('.vbatText'),
                        
                        // Energy today
                        solar_today: parseValue('#todayYieldingText'),
                        export_today: parseValue('#todayExportText'),
                        import_today: parseValue('#todayImportText'),
                        consumption_today: parseValue('#todayUsageText'),
                        
                        // System status
                        system_status: document.querySelector('#infoListLabel')?.textContent || 'Unknown',
                        
                        // Grid
                        grid_voltage: parseValue('.vacText'),
                        grid_frequency: parseValue('.facText')
                    };
                }
            """)
            
            return data
            
        except Exception as e:
            print(f"Error getting data: {e}")
            return None
    
    def format_power(self, value):
        """Format power value with color"""
        if value is None:
            return "---"
        
        val = int(value)
        if val > 0:
            return f"+{val}"
        elif val < 0:
            return f"{val}"
        else:
            return "0"
    
    def create_power_bar(self, value, max_val=10000, width=20):
        """Create a visual power bar"""
        if value is None:
            return "─" * width
        
        abs_val = abs(value)
        filled = int(width * abs_val / max_val)
        filled = min(filled, width)
        
        if value > 0:
            return "▸" * filled + "─" * (width - filled)
        elif value < 0:
            return "─" * (width - filled) + "◂" * filled
        else:
            return "─" * width
    
    async def display_dashboard(self, data):
        """Display data in dashboard format"""
        if not data:
            print("No data available")
            return
        
        # Clear screen
        print("\033[2J\033[H", end='')
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Header
        print(f"╔{'═'*78}╗")
        print(f"║ EG4 LIVE DASHBOARD - {timestamp}".ljust(77) + " ║")
        print(f"╠{'═'*78}╣")
        
        # Power Flow Section
        print(f"║ POWER FLOW".ljust(77) + " ║")
        print(f"║ {'─'*76} ║")
        
        # Solar
        pv = data.get('pv_total', 0)
        print(f"║ ☀️  Solar    : {self.format_power(pv):>6} W  {self.create_power_bar(pv)}".ljust(77) + " ║")
        
        # Battery
        battery = data.get('battery_power', 0)
        soc = data.get('battery_soc', 0)
        voltage = data.get('battery_voltage', 0)
        battery_info = f"[{soc}% {voltage}V]"
        print(f"║ 🔋 Battery  : {self.format_power(battery):>6} W  {self.create_power_bar(battery)} {battery_info}".ljust(77) + " ║")
        
        # Grid
        grid = data.get('grid_power', 0)
        grid_v = data.get('grid_voltage', 0)
        grid_hz = data.get('grid_frequency', 0)
        grid_info = f"[{grid_v}V {grid_hz}Hz]"
        print(f"║ ⚡ Grid     : {self.format_power(grid):>6} W  {self.create_power_bar(grid)} {grid_info}".ljust(77) + " ║")
        
        # Load
        load = data.get('load_power', 0)
        print(f"║ 🏠 Load     : {self.format_power(load):>6} W  {self.create_power_bar(load, 5000)}".ljust(77) + " ║")
        
        # Energy Today Section
        print(f"║ {'─'*76} ║")
        print(f"║ TODAY'S ENERGY".ljust(77) + " ║")
        print(f"║ {'─'*76} ║")
        
        solar_today = data.get('solar_today', 0)
        export_today = data.get('export_today', 0)
        import_today = data.get('import_today', 0)
        consumption_today = data.get('consumption_today', 0)
        
        print(f"║ Solar: {solar_today:>6.1f} kWh  │  Export: {export_today:>6.1f} kWh  │  "
              f"Import: {import_today:>6.1f} kWh  │  Load: {consumption_today:>6.1f} kWh".ljust(77) + " ║")
        
        # Status
        print(f"║ {'─'*76} ║")
        status = data.get('system_status', 'Unknown')
        print(f"║ Status: {status}".ljust(77) + " ║")
        
        # Footer
        print(f"╚{'═'*78}╝")
        
        # Energy flow summary
        print("\nENERGY FLOW:")
        if pv > 50:
            print(f"  Solar ({pv}W) →", end='')
            
            if battery > 50:
                print(f" Battery ({battery}W) +", end='')
            elif battery < -50:
                print(f" [Battery ({abs(battery)}W) ←]", end='')
                
            if grid < -50:
                print(f" Grid ({abs(grid)}W) +", end='')
            elif grid > 50:
                print(f" [Grid ({grid}W) ←]", end='')
                
            print(f" = Load ({load}W)")
        else:
            # No solar
            sources = []
            if battery < -50:
                sources.append(f"Battery ({abs(battery)}W)")
            if grid > 50:
                sources.append(f"Grid ({grid}W)")
            
            if sources:
                print(f"  {' + '.join(sources)} → Load ({load}W)")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
    
    async def run_continuous(self, interval=10):
        """Run continuous monitoring"""
        await self.start(headless=True)
        
        try:
            print("Logging into EG4 cloud monitor...")
            if not await self.login():
                print("Login failed")
                return
                
            print("Login successful! Starting dashboard...\n")
            await asyncio.sleep(2)
            
            while True:
                try:
                    data = await self.get_live_data()
                    await self.display_dashboard(data)
                    
                    await asyncio.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopping dashboard...")
        finally:
            await self.close()

async def main():
    """Main function"""
    print("EG4 Live Dashboard")
    print("="*50)
    print("Real-time monitoring with 10-second updates")
    print("Press Ctrl+C to stop\n")
    
    dashboard = EG4LiveDashboard()
    await dashboard.run_continuous(interval=10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")