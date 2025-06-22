#!/usr/bin/env python3
"""
EG4 Monitor - Comprehensive monitoring for EG4 inverters via cloud portal
Combines all features from previous monitors into one unified program
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv
import json
import argparse

load_dotenv()

class EG4Monitor:
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
    
    async def wait_for_data(self):
        """Wait for real data to load on the page"""
        for i in range(30):
            await asyncio.sleep(1)
            soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
            if soc and soc != '--':
                return True
        return False
    
    async def navigate_to_monitor(self):
        """Navigate to the monitor page and wait for data"""
        await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
        
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
                        if (!text || text === '--' || text === '') return '--';
                        return text.trim();
                    };
                    
                    // === REAL-TIME DATA ===
                    
                    // Battery Status
                    data.battery = {
                        power: cleanText(document.querySelector('.batteryPowerText')?.textContent),
                        soc: cleanText(document.querySelector('.socText')?.textContent),
                        voltage: cleanText(document.querySelector('.vbatText')?.textContent),
                        current: cleanText(document.querySelector('.batteryCurrentText')?.textContent),
                        bms_charge_limit: cleanText(document.querySelector('.maxChgCurrText')?.textContent),
                        bms_discharge_limit: cleanText(document.querySelector('.maxDischgCurrText')?.textContent),
                        bms_charge_status: cleanText(document.querySelector('.bmsChargeText')?.textContent),
                        bms_discharge_status: cleanText(document.querySelector('.bmsDischargeText')?.textContent),
                        bms_force_charge: cleanText(document.querySelector('.bmsForceChargeText')?.textContent),
                        capacity: cleanText(document.querySelector('.batteryCapacityText')?.textContent)
                    };
                    
                    // PV Status
                    data.pv = {
                        pv1_power: cleanText(document.querySelector('.pv1PowerText')?.textContent),
                        pv1_voltage: cleanText(document.querySelector('.vpv1Text')?.textContent),
                        pv1_current: cleanText(document.querySelector('.ipv1Text')?.textContent),
                        pv2_power: cleanText(document.querySelector('.pv2PowerText')?.textContent),
                        pv2_voltage: cleanText(document.querySelector('.vpv2Text')?.textContent),
                        pv2_current: cleanText(document.querySelector('.ipv2Text')?.textContent),
                        pv3_power: cleanText(document.querySelector('.pv3PowerText')?.textContent),
                        pv3_voltage: cleanText(document.querySelector('.vpv3Text')?.textContent),
                        pv3_current: cleanText(document.querySelector('.ipv3Text')?.textContent),
                        total_power: cleanText(document.querySelector('.pvPowerText')?.textContent)
                    };
                    
                    // Grid Status
                    data.grid = {
                        power: cleanText(document.querySelector('.gridPowerText')?.textContent),
                        voltage: cleanText(document.querySelector('.vacText')?.textContent),
                        frequency: cleanText(document.querySelector('.facText')?.textContent),
                        current: cleanText(document.querySelector('.igridText')?.textContent)
                    };
                    
                    // Load/Consumption
                    data.load = {
                        power: cleanText(document.querySelector('.consumptionPowerText')?.textContent),
                        percentage: cleanText(document.querySelector('.loadPercentText')?.textContent),
                        current: cleanText(document.querySelector('.iloadText')?.textContent)
                    };
                    
                    // EPS/Backup
                    data.eps = {
                        power: cleanText(document.querySelector('.epsPowerText')?.textContent),
                        l1n: cleanText(document.querySelector('.epsL1nText')?.textContent),
                        l2n: cleanText(document.querySelector('.epsL2nText')?.textContent),
                        status: cleanText(document.querySelector('.standByLine')?.textContent)
                    };
                    
                    // Inverter Info
                    data.inverter = {
                        status: cleanText(document.querySelector('.statusText')?.textContent),
                        temperature: cleanText(document.querySelector('.tempText')?.textContent),
                        model: cleanText(document.querySelector('.modelText')?.textContent)
                    };
                    
                    // Generator
                    data.generator = {
                        dry_contact: cleanText(document.querySelector('.genDryContactText')?.textContent)
                    };
                    
                    // === ENERGY STATISTICS ===
                    
                    // Solar Yield
                    data.solar_yield = {
                        today: cleanText(document.querySelector('#todayYieldingText')?.textContent),
                        total: cleanText(document.querySelector('#totalYieldingText')?.textContent),
                        load_today: cleanText(document.querySelector('#pvLoadTodaySpan')?.textContent),
                        charge_today: cleanText(document.querySelector('#pvChargeTodaySpan')?.textContent),
                        export_today: cleanText(document.querySelector('#pvExportTodaySpan')?.textContent)
                    };
                    
                    // Battery Statistics
                    data.battery_stats = {
                        discharged_today: cleanText(document.querySelector('#todayDischargingText')?.textContent),
                        charged_today: cleanText(document.querySelector('#todayChargingText')?.textContent),
                        total_discharged: cleanText(document.querySelector('#totalDischargingText')?.textContent),
                        total_charged: cleanText(document.querySelector('#totalChargingText')?.textContent)
                    };
                    
                    // Grid Exchange
                    data.grid_exchange = {
                        export_today: cleanText(document.querySelector('#todayExportText')?.textContent),
                        import_today: cleanText(document.querySelector('#todayImportText')?.textContent),
                        total_export: cleanText(document.querySelector('#totalExportText')?.textContent),
                        total_import: cleanText(document.querySelector('#totalImportText')?.textContent)
                    };
                    
                    // Consumption
                    data.consumption = {
                        today: cleanText(document.querySelector('#todayUsageText')?.textContent),
                        total: cleanText(document.querySelector('#totalUsageText')?.textContent)
                    };
                    
                    // === SYSTEM INFO ===
                    
                    // System Status and Time
                    data.system = {
                        status: cleanText(document.querySelector('#infoListLabel')?.textContent),
                        time: cleanText(document.querySelector('#localTimeLabel')?.textContent)
                    };
                    
                    // Weather Data (if available)
                    data.weather = {
                        temperature: cleanText(document.querySelector('.temp')?.textContent),
                        location: cleanText(document.querySelector('.resolvedAddress')?.textContent),
                        condition: cleanText(document.querySelector('.weatherText')?.textContent),
                        today_predicted: cleanText(document.querySelector('.predictSolarToday')?.textContent),
                        tomorrow_predicted: cleanText(document.querySelector('.predictSolarTomorrow')?.textContent)
                    };
                    
                    return data;
                }
            """)
            
            return stats
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            return None
    
    def display_realtime(self, stats):
        """Display real-time data in a clean, compact format"""
        if not stats:
            print("No data available")
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Clear screen for clean display
        print("\033[2J\033[H")  # Clear screen and move cursor to top
        
        print(f"{'='*80}")
        print(f"EG4 MONITOR - {timestamp}")
        print(f"{'='*80}")
        
        # System Status
        print(f"\n⚙️  SYSTEM: {stats['system']['status']} | Time: {stats['system']['time']}")
        
        # Battery Section with visual bar
        print(f"\n🔋 BATTERY")
        soc = stats['battery']['soc']
        power = stats['battery']['power']
        
        if soc != '--':
            try:
                soc_val = int(soc.replace('%', ''))
                bar_length = 40
                filled = int(bar_length * soc_val / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                # Determine charging/discharging status
                if power != '--':
                    power_val = int(power.replace('W', '').replace(',', '').strip())
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
        
        print(f"  Power: {power:>8} W | Voltage: {stats['battery']['voltage']} V | Current: {stats['battery']['current']} A")
        print(f"  BMS Limits: Charge {stats['battery']['bms_charge_limit']} A | Discharge {stats['battery']['bms_discharge_limit']} A")
        print(f"  BMS Status: Charge {stats['battery']['bms_charge_status']} | Discharge {stats['battery']['bms_discharge_status']}")
        
        # PV Section
        print(f"\n☀️  SOLAR")
        total_pv = 0
        for i in range(1, 4):
            pv_power = stats['pv'][f'pv{i}_power']
            pv_voltage = stats['pv'][f'pv{i}_voltage']
            pv_current = stats['pv'][f'pv{i}_current']
            if pv_power != '--' and pv_power != '0':
                print(f"  PV{i}: {pv_power:>8} W  ({pv_voltage} V, {pv_current} A)")
                try:
                    total_pv += int(pv_power.replace(',', ''))
                except:
                    pass
        
        if total_pv > 0:
            print(f"  {'─'*40}")
            print(f"  Total: {total_pv:>7} W")
        
        # Power Flow
        print(f"\n⚡ POWER FLOW")
        print(f"  Solar  → {total_pv:>7} W")
        print(f"  Grid   ⇄ {stats['grid']['power']:>7} W  ({stats['grid']['voltage']} V @ {stats['grid']['frequency']} Hz)")
        print(f"  Load   ← {stats['load']['power']:>7} W  ({stats['load']['percentage']}% of capacity)")
        print(f"  Battery ⇄ {stats['battery']['power']:>7} W")
        
        # EPS/Backup
        if stats['eps']['status'] != '--':
            print(f"\n🔌 BACKUP/EPS: {stats['eps']['status']}")
            if stats['eps']['power'] != '--' and stats['eps']['power'] != '0':
                print(f"  Power: {stats['eps']['power']} W | L1-N: {stats['eps']['l1n']} W | L2-N: {stats['eps']['l2n']} W")
        
        # Generator
        if stats['generator']['dry_contact'] != '--':
            print(f"\n🏭 GENERATOR: {stats['generator']['dry_contact']}")
        
        # Today's Statistics
        print(f"\n📊 TODAY'S ENERGY")
        print(f"  Solar Yield:     {stats['solar_yield']['today']:>8} kWh", end="")
        if stats['solar_yield']['load_today'] != '--':
            print(f"  (Load: {stats['solar_yield']['load_today']} | Charge: {stats['solar_yield']['charge_today']} | Export: {stats['solar_yield']['export_today']})")
        else:
            print()
        
        print(f"  Consumption:     {stats['consumption']['today']:>8} kWh")
        print(f"  Grid Import:     {stats['grid_exchange']['import_today']:>8} kWh")
        print(f"  Grid Export:     {stats['grid_exchange']['export_today']:>8} kWh")
        print(f"  Battery Charge:  {stats['battery_stats']['charged_today']:>8} kWh")
        print(f"  Battery Discharge:{stats['battery_stats']['discharged_today']:>7} kWh")
        
        # Lifetime Statistics
        print(f"\n📈 LIFETIME")
        print(f"  Total Generated: {stats['solar_yield']['total']:>12} kWh")
        print(f"  Total Consumed:  {stats['consumption']['total']:>12} kWh")
        print(f"  Total Imported:  {stats['grid_exchange']['total_import']:>12} kWh")
        print(f"  Total Exported:  {stats['grid_exchange']['total_export']:>12} kWh")
        
        # Weather (if available)
        if stats['weather']['location'] != '--':
            print(f"\n🌤️  WEATHER")
            print(f"  Location: {stats['weather']['location']} | Temp: {stats['weather']['temperature']} | {stats['weather']['condition']}")
            if stats['weather']['today_predicted'] != '--':
                print(f"  Solar Prediction: Today {stats['weather']['today_predicted']} kWh | Tomorrow {stats['weather']['tomorrow_predicted']} kWh")
        
        # Inverter Status
        if stats['inverter']['temperature'] != '--':
            print(f"\n🌡️  INVERTER: {stats['inverter']['temperature']}")
        
        print(f"\n{'='*80}")
        print("Press Ctrl+C to exit | Updates every 30 seconds")
    
    def display_detailed(self, stats):
        """Display detailed statistics (similar to full stats monitor)"""
        if not stats:
            print("No data available")
            return
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*80}")
        print(f"EG4 DETAILED SYSTEM STATUS - {timestamp}")
        print(f"{'='*80}")
        
        # ENERGY OVERVIEW
        print(f"\n📊 ENERGY OVERVIEW")
        print(f"{'─'*40}")
        print(f"Solar Yield:")
        print(f"  Today: {stats['solar_yield']['today']} kWh")
        print(f"  Total: {stats['solar_yield']['total']} kWh")
        if stats['solar_yield']['load_today'] != '--':
            print(f"  Distribution Today: Load {stats['solar_yield']['load_today']} | "
                  f"Charge {stats['solar_yield']['charge_today']} | "
                  f"Export {stats['solar_yield']['export_today']}")
        
        print(f"\nBattery Energy:")
        print(f"  Discharged Today: {stats['battery_stats']['discharged_today']} kWh")
        print(f"  Charged Today: {stats['battery_stats']['charged_today']} kWh")
        print(f"  Total Discharged: {stats['battery_stats']['total_discharged']} kWh")
        print(f"  Total Charged: {stats['battery_stats']['total_charged']} kWh")
        
        print(f"\nGrid Exchange:")
        print(f"  Export Today: {stats['grid_exchange']['export_today']} kWh")
        print(f"  Import Today: {stats['grid_exchange']['import_today']} kWh")
        print(f"  Total Export: {stats['grid_exchange']['total_export']} kWh")
        print(f"  Total Import: {stats['grid_exchange']['total_import']} kWh")
        
        print(f"\nConsumption:")
        print(f"  Today: {stats['consumption']['today']} kWh")
        print(f"  Total: {stats['consumption']['total']} kWh")
        
        # Continue with remaining sections...
        print(f"\n{'='*80}")
    
    async def save_to_json(self, stats, filename=None):
        """Save statistics to JSON file"""
        if stats:
            if not filename:
                filename = f"eg4_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(stats, f, indent=2)
            print(f"\nData saved to {filename}")
    
    async def run_once(self, display_mode='realtime', save_json=False):
        """Run once and display data"""
        await self.start(headless=True)
        
        try:
            print("Logging into EG4 cloud monitor...")
            if await self.login():
                print("Login successful! Loading data...")
                
                if await self.navigate_to_monitor():
                    stats = await self.extract_all_data()
                    
                    if display_mode == 'realtime':
                        self.display_realtime(stats)
                    else:
                        self.display_detailed(stats)
                    
                    if save_json:
                        await self.save_to_json(stats)
                    
                    return stats
                else:
                    print("Failed to load monitor data")
            else:
                print("Login failed")
        finally:
            await self.close()
            
        return None
    
    async def run_continuous(self, interval=30, display_mode='realtime'):
        """Run continuous monitoring"""
        await self.start(headless=True)
        
        try:
            if not await self.login():
                print("Login failed")
                return
                
            print("Login successful!")
            
            if not await self.navigate_to_monitor():
                print("Failed to load initial data")
                return
            
            print(f"\nStarting continuous monitoring (updates every {interval}s)")
            print("Press Ctrl+C to stop\n")
            
            loop_count = 0
            while True:
                try:
                    stats = await self.extract_all_data()
                    
                    if display_mode == 'realtime':
                        self.display_realtime(stats)
                    else:
                        self.display_detailed(stats)
                    
                    # Reload page every 5 minutes to ensure fresh data
                    loop_count += 1
                    if loop_count >= (300 / interval):  # 5 minutes
                        await self.page.reload(wait_until='networkidle')
                        await self.wait_for_data()
                        loop_count = 0
                    
                    await asyncio.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        finally:
            await self.close()
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()

async def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='EG4 Cloud Monitor - Monitor your EG4 inverter')
    parser.add_argument('--mode', choices=['once', 'continuous'], default='continuous',
                        help='Run mode: once or continuous (default: continuous)')
    parser.add_argument('--display', choices=['realtime', 'detailed'], default='realtime',
                        help='Display mode: realtime or detailed (default: realtime)')
    parser.add_argument('--interval', type=int, default=30,
                        help='Update interval in seconds for continuous mode (default: 30)')
    parser.add_argument('--save-json', action='store_true',
                        help='Save data to JSON file (only in once mode)')
    
    args = parser.parse_args()
    
    print("EG4 Cloud Monitor")
    print("="*80)
    print(f"Account: {os.getenv('EG4_MONITOR_USERNAME')}")
    print()
    
    monitor = EG4Monitor()
    
    if args.mode == 'once':
        await monitor.run_once(display_mode=args.display, save_json=args.save_json)
    else:
        await monitor.run_continuous(interval=args.interval, display_mode=args.display)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")