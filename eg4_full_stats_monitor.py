#!/usr/bin/env python3
"""
EG4 Full Statistics Monitor - Extract all live data from monitor.eg4electronics.com
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv
import re
import json

load_dotenv()

class EG4FullStatsMonitor:
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
            
            if 'login' not in self.page.url:
                return True
            return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def get_all_stats(self):
        """Extract all statistics from the monitor page"""
        try:
            # Navigate to monitor page
            await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
            
            # Wait for data to load
            for i in range(30):
                await asyncio.sleep(1)
                soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
                if soc and soc != '--':
                    break
            else:
                print("Warning: Data did not load after 30 seconds")
            
            # Extract all data using JavaScript
            stats = await self.page.evaluate("""
                () => {
                    let data = {};
                    
                    // === ENERGY INFO SECTION ===
                    // Solar Yield
                    data.solar_yield = {
                        today: document.querySelector('#todayYieldingText')?.textContent || '--',
                        total: document.querySelector('#totalYieldingText')?.textContent || '--',
                        load_today: document.querySelector('#pvLoadTodaySpan')?.textContent || '--',
                        charge_today: document.querySelector('#pvChargeTodaySpan')?.textContent || '--',
                        export_today: document.querySelector('#pvExportTodaySpan')?.textContent || '--'
                    };
                    
                    // Battery
                    data.battery = {
                        discharged_today: document.querySelector('#todayDischargingText')?.textContent || '--',
                        total_discharged: document.querySelector('#totalDischargingText')?.textContent || '--',
                        charged_today: document.querySelector('#todayChargingText')?.textContent || '--',
                        total_charged: document.querySelector('#totalChargingText')?.textContent || '--'
                    };
                    
                    // Feed-in/Export
                    data.export = {
                        today: document.querySelector('#todayExportText')?.textContent || '--',
                        total: document.querySelector('#totalExportText')?.textContent || '--'
                    };
                    
                    // Import
                    data.import = {
                        today: document.querySelector('#todayImportText')?.textContent || '--',
                        total: document.querySelector('#totalImportText')?.textContent || '--'
                    };
                    
                    // Consumption
                    data.consumption = {
                        today: document.querySelector('#todayUsageText')?.textContent || '--',
                        total: document.querySelector('#totalUsageText')?.textContent || '--'
                    };
                    
                    // === SYSTEM INFORMATION SECTION ===
                    // Battery Status
                    data.battery_status = {
                        power: document.querySelector('.batteryPowerText')?.textContent || '--',
                        soc: document.querySelector('.socText')?.textContent || '--',
                        voltage: document.querySelector('.vbatText')?.textContent || '--',
                        bms_charge_limit: document.querySelector('.maxChgCurrText')?.textContent || '--',
                        bms_discharge_limit: document.querySelector('.maxDischgCurrText')?.textContent || '--',
                        bms_charge_status: document.querySelector('.bmsChargeText')?.textContent || '--',
                        bms_discharge_status: document.querySelector('.bmsDischargeText')?.textContent || '--',
                        bms_force_charge: document.querySelector('.bmsForceChargeText')?.textContent || '--'
                    };
                    
                    // PV Status
                    data.pv = {
                        pv1_power: document.querySelector('.pv1PowerText')?.textContent || '--',
                        pv1_voltage: document.querySelector('.vpv1Text')?.textContent || '--',
                        pv2_power: document.querySelector('.pv2PowerText')?.textContent || '--',
                        pv2_voltage: document.querySelector('.vpv2Text')?.textContent || '--',
                        pv3_power: document.querySelector('.pv3PowerText')?.textContent || '--',
                        pv3_voltage: document.querySelector('.vpv3Text')?.textContent || '--'
                    };
                    
                    // Grid Status
                    data.grid = {
                        power: document.querySelector('.gridPowerText')?.textContent || '--',
                        voltage: document.querySelector('.vacText')?.textContent || '--',
                        frequency: document.querySelector('.facText')?.textContent || '--'
                    };
                    
                    // Consumption/Load
                    data.load = {
                        power: document.querySelector('.consumptionPowerText')?.textContent || '--'
                    };
                    
                    // EPS/Backup
                    data.eps = {
                        power: document.querySelector('.epsPowerText')?.textContent || '--',
                        l1n: document.querySelector('.epsL1nText')?.textContent || '--',
                        l2n: document.querySelector('.epsL2nText')?.textContent || '--',
                        status: document.querySelector('.standByLine')?.textContent || '--'
                    };
                    
                    // System Time
                    data.system_time = document.querySelector('#localTimeLabel')?.textContent || '--';
                    
                    // System Status
                    data.system_status = document.querySelector('#infoListLabel')?.textContent || '--';
                    
                    // Weather Data (if available)
                    data.weather = {
                        temperature: document.querySelector('.temp')?.textContent || '--',
                        location: document.querySelector('.resolvedAddress')?.textContent || '--',
                        condition: document.querySelector('.weatherText')?.textContent || '--',
                        today_predicted: document.querySelector('.predictSolarToday')?.textContent || '--',
                        tomorrow_predicted: document.querySelector('.predictSolarTomorrow')?.textContent || '--'
                    };
                    
                    // Generator Status
                    data.generator = {
                        dry_contact: document.querySelector('.genDryContactText')?.textContent || '--'
                    };
                    
                    return data;
                }
            """)
            
            return stats
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return None
    
    def format_value(self, value, unit=''):
        """Format value with unit"""
        if value == '--' or value is None:
            return '--'
        return f"{value} {unit}".strip()
    
    async def display_stats(self, stats):
        """Display all statistics in organized format"""
        if not stats:
            print("No data available")
            return
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*80}")
        print(f"EG4 FULL SYSTEM STATUS - {timestamp}")
        print(f"{'='*80}")
        
        # ENERGY OVERVIEW
        print(f"\n📊 ENERGY OVERVIEW")
        print(f"{'─'*40}")
        print(f"Solar Yield:")
        print(f"  Today: {self.format_value(stats['solar_yield']['today'], 'kWh')}")
        print(f"  Total: {self.format_value(stats['solar_yield']['total'], 'kWh')}")
        print(f"  Distribution Today: Load {stats['solar_yield']['load_today']} | "
              f"Charge {stats['solar_yield']['charge_today']} | "
              f"Export {stats['solar_yield']['export_today']}")
        
        print(f"\nBattery Energy:")
        print(f"  Discharged Today: {self.format_value(stats['battery']['discharged_today'], 'kWh')}")
        print(f"  Charged Today: {self.format_value(stats['battery']['charged_today'], 'kWh')}")
        print(f"  Total Discharged: {self.format_value(stats['battery']['total_discharged'], 'kWh')}")
        print(f"  Total Charged: {self.format_value(stats['battery']['total_charged'], 'kWh')}")
        
        print(f"\nGrid Exchange:")
        print(f"  Export Today: {self.format_value(stats['export']['today'], 'kWh')}")
        print(f"  Import Today: {self.format_value(stats['import']['today'], 'kWh')}")
        print(f"  Total Export: {self.format_value(stats['export']['total'], 'kWh')}")
        print(f"  Total Import: {self.format_value(stats['import']['total'], 'kWh')}")
        
        print(f"\nConsumption:")
        print(f"  Today: {self.format_value(stats['consumption']['today'], 'kWh')}")
        print(f"  Total: {self.format_value(stats['consumption']['total'], 'kWh')}")
        
        # REAL-TIME STATUS
        print(f"\n⚡ REAL-TIME STATUS")
        print(f"{'─'*40}")
        print(f"System Status: {stats['system_status']}")
        print(f"System Time: {stats['system_time']}")
        
        print(f"\nBattery:")
        print(f"  SOC: {self.format_value(stats['battery_status']['soc'], '%')}")
        print(f"  Voltage: {self.format_value(stats['battery_status']['voltage'], 'Vdc')}")
        print(f"  Power: {self.format_value(stats['battery_status']['power'], 'W')}")
        print(f"  BMS Limits: Charge {self.format_value(stats['battery_status']['bms_charge_limit'], 'A')} | "
              f"Discharge {self.format_value(stats['battery_status']['bms_discharge_limit'], 'A')}")
        print(f"  BMS Status: Charge {stats['battery_status']['bms_charge_status']} | "
              f"Discharge {stats['battery_status']['bms_discharge_status']}")
        
        print(f"\nSolar PV:")
        print(f"  PV1: {self.format_value(stats['pv']['pv1_power'], 'W')} @ {self.format_value(stats['pv']['pv1_voltage'], 'V')}")
        print(f"  PV2: {self.format_value(stats['pv']['pv2_power'], 'W')} @ {self.format_value(stats['pv']['pv2_voltage'], 'V')}")
        print(f"  PV3: {self.format_value(stats['pv']['pv3_power'], 'W')} @ {self.format_value(stats['pv']['pv3_voltage'], 'V')}")
        
        # Calculate total PV power
        try:
            pv_total = 0
            for i in range(1, 4):
                pv_power = stats['pv'][f'pv{i}_power']
                if pv_power and pv_power != '--':
                    pv_total += int(pv_power)
            print(f"  Total PV: {pv_total} W")
        except:
            pass
        
        print(f"\nGrid:")
        print(f"  Power: {self.format_value(stats['grid']['power'], 'W')}")
        print(f"  Voltage: {self.format_value(stats['grid']['voltage'], 'Vac')}")
        print(f"  Frequency: {self.format_value(stats['grid']['frequency'], 'Hz')}")
        
        print(f"\nLoad: {self.format_value(stats['load']['power'], 'W')}")
        
        print(f"\nBackup/EPS:")
        print(f"  Status: {stats['eps']['status']}")
        print(f"  Power: {self.format_value(stats['eps']['power'], 'W')}")
        print(f"  L1-N: {self.format_value(stats['eps']['l1n'], 'W')}")
        print(f"  L2-N: {self.format_value(stats['eps']['l2n'], 'W')}")
        
        print(f"\nGenerator: {stats['generator']['dry_contact']}")
        
        # WEATHER (if available)
        if stats['weather']['location'] != '--':
            print(f"\n🌤️  WEATHER & PREDICTION")
            print(f"{'─'*40}")
            print(f"Location: {stats['weather']['location']}")
            print(f"Temperature: {stats['weather']['temperature']}")
            print(f"Condition: {stats['weather']['condition']}")
            print(f"Solar Prediction:")
            print(f"  Today: {self.format_value(stats['weather']['today_predicted'], 'kWh')}")
            print(f"  Tomorrow: {self.format_value(stats['weather']['tomorrow_predicted'], 'kWh')}")
        
        print(f"\n{'='*80}")
    
    async def save_to_json(self, stats):
        """Save statistics to JSON file"""
        if stats:
            filename = f"eg4_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(stats, f, indent=2)
            print(f"Data saved to {filename}")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
    
    async def run_once(self):
        """Run once and get all statistics"""
        await self.start(headless=True)
        
        try:
            print("Logging into EG4 cloud monitor...")
            if await self.login():
                print("Login successful! Retrieving statistics...")
                stats = await self.get_all_stats()
                await self.display_stats(stats)
                return stats
        finally:
            await self.close()
            
        return None
    
    async def run_continuous(self, interval=60):
        """Run continuous monitoring"""
        await self.start(headless=True)
        
        try:
            if not await self.login():
                print("Login failed")
                return
                
            print("Login successful!")
            print(f"\nMonitoring all statistics every {interval} seconds")
            print("Press Ctrl+C to stop\n")
            
            while True:
                try:
                    stats = await self.get_all_stats()
                    
                    # Clear screen for clean display
                    print("\033[2J\033[H", end='')
                    
                    await self.display_stats(stats)
                    
                    # Optionally save to JSON
                    # await self.save_to_json(stats)
                    
                    await asyncio.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        finally:
            await self.close()

async def main():
    """Main function"""
    print("EG4 Full Statistics Monitor")
    print("="*80)
    print(f"Account: {os.getenv('EG4_MONITOR_USERNAME')}")
    print()
    
    monitor = EG4FullStatsMonitor()
    
    # Run once first
    stats = await monitor.run_once()
    
    if stats:
        print("\n✓ Successfully retrieved all statistics!")
        
        # Ask about continuous monitoring
        try:
            response = input("\nStart continuous monitoring? (y/n): ")
            if response.lower() == 'y':
                interval = input("Update interval in seconds (default 60): ")
                interval = int(interval) if interval else 60
                
                monitor = EG4FullStatsMonitor()  # New instance
                await monitor.run_continuous(interval=interval)
        except EOFError:
            # Running in non-interactive mode
            print("\nRunning in continuous mode (60s interval)...")
            monitor = EG4FullStatsMonitor()
            await monitor.run_continuous(interval=60)
    else:
        print("\n✗ Failed to retrieve statistics")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")