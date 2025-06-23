#!/usr/bin/env python3
"""
EG4 Data Logger - Log all statistics to CSV for analysis
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv
import csv
import json

load_dotenv()

class EG4DataLogger:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.browser = None
        self.page = None
        self.csv_filename = f"eg4_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.first_write = True
        
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
    
    async def get_all_data(self):
        """Get all available data from the page"""
        try:
            await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Extract everything
            data = await self.page.evaluate("""
                () => {
                    const getValue = (selector) => {
                        const elem = document.querySelector(selector);
                        if (!elem) return null;
                        const text = elem.textContent.trim();
                        return text || null;
                    };
                    
                    return {
                        timestamp: new Date().toISOString(),
                        
                        // Energy totals
                        solar_yield_today: getValue('#todayYieldingText'),
                        solar_yield_total: getValue('#totalYieldingText'),
                        battery_discharged_today: getValue('#todayDischargingText'),
                        battery_discharged_total: getValue('#totalDischargingText'),
                        battery_charged_today: getValue('#todayChargingText'),
                        battery_charged_total: getValue('#totalChargingText'),
                        export_today: getValue('#todayExportText'),
                        export_total: getValue('#totalExportText'),
                        import_today: getValue('#todayImportText'),
                        import_total: getValue('#totalImportText'),
                        consumption_today: getValue('#todayUsageText'),
                        consumption_total: getValue('#totalUsageText'),
                        
                        // Real-time values
                        battery_power: getValue('.batteryPowerText'),
                        battery_soc: getValue('.socText'),
                        battery_voltage: getValue('.vbatText'),
                        
                        pv1_power: getValue('.pv1PowerText'),
                        pv1_voltage: getValue('.vpv1Text'),
                        pv2_power: getValue('.pv2PowerText'),
                        pv2_voltage: getValue('.vpv2Text'),
                        pv3_power: getValue('.pv3PowerText'),
                        pv3_voltage: getValue('.vpv3Text'),
                        
                        grid_power: getValue('.gridPowerText'),
                        grid_voltage: getValue('.vacText'),
                        grid_frequency: getValue('.facText'),
                        
                        load_power: getValue('.consumptionPowerText'),
                        
                        eps_power: getValue('.epsPowerText'),
                        eps_l1n: getValue('.epsL1nText'),
                        eps_l2n: getValue('.epsL2nText'),
                        
                        // BMS info
                        bms_charge_limit: getValue('.maxChgCurrText'),
                        bms_discharge_limit: getValue('.maxDischgCurrText'),
                        bms_charge_status: getValue('.bmsChargeText'),
                        bms_discharge_status: getValue('.bmsDischargeText'),
                        bms_force_charge: getValue('.bmsForceChargeText'),
                        
                        // System info
                        system_status: getValue('#infoListLabel'),
                        system_time: getValue('#localTimeLabel'),
                        generator_status: getValue('.genDryContactText'),
                        
                        // Weather (if available)
                        weather_temp: getValue('.temp'),
                        weather_location: getValue('.resolvedAddress'),
                        weather_condition: getValue('.weatherText'),
                        solar_predict_today: getValue('.predictSolarToday'),
                        solar_predict_tomorrow: getValue('.predictSolarTomorrow')
                    };
                }
            """)
            
            return data
            
        except Exception as e:
            print(f"Error getting data: {e}")
            return None
    
    def save_to_csv(self, data):
        """Save data to CSV file"""
        if not data:
            return
            
        # Convert all values to float where possible
        processed_data = {}
        for key, value in data.items():
            if value and value != '--':
                try:
                    # Try to extract numeric value
                    if isinstance(value, str):
                        # Remove units and convert
                        numeric = ''.join(c for c in value if c.isdigit() or c in '.-')
                        if numeric:
                            processed_data[key] = float(numeric)
                        else:
                            processed_data[key] = value
                    else:
                        processed_data[key] = value
                except:
                    processed_data[key] = value
            else:
                processed_data[key] = None
        
        # Write to CSV
        if self.first_write:
            # Write header
            with open(self.csv_filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=processed_data.keys())
                writer.writeheader()
                writer.writerow(processed_data)
            self.first_write = False
            print(f"Created log file: {self.csv_filename}")
        else:
            # Append data
            with open(self.csv_filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=processed_data.keys())
                writer.writerow(processed_data)
    
    def display_summary(self, data):
        """Display current values summary"""
        if not data:
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Extract key values
        pv_total = 0
        try:
            for i in range(1, 4):
                pv = data.get(f'pv{i}_power', '0')
                if pv and pv != '--':
                    pv_total += float(pv)
        except:
            pass
        
        print(f"[{timestamp}] "
              f"PV: {pv_total:.0f}W | "
              f"Battery: {data.get('battery_power', '--')}W @ {data.get('battery_soc', '--')}% | "
              f"Grid: {data.get('grid_power', '--')}W | "
              f"Load: {data.get('load_power', '--')}W | "
              f"Today: {data.get('solar_yield_today', '--')}kWh")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
    
    async def run_logger(self, interval=60):
        """Run continuous logging"""
        await self.start(headless=True)
        
        try:
            print("EG4 Data Logger")
            print("="*60)
            print("Logging into EG4 cloud monitor...")
            
            if not await self.login():
                print("Login failed")
                return
                
            print("Login successful!")
            print(f"Logging data every {interval} seconds")
            print("Press Ctrl+C to stop\n")
            
            log_count = 0
            
            while True:
                try:
                    data = await self.get_all_data()
                    
                    if data:
                        self.save_to_csv(data)
                        self.display_summary(data)
                        log_count += 1
                        
                        if log_count % 10 == 0:
                            print(f"\n📊 {log_count} data points logged to {self.csv_filename}")
                    
                    await asyncio.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                    
        except KeyboardInterrupt:
            print(f"\n\nStopping logger...")
            print(f"Total data points logged: {log_count}")
            print(f"Data saved to: {self.csv_filename}")
        finally:
            await self.close()

async def main():
    """Main function"""
    logger = EG4DataLogger()
    
    # Ask for logging interval
    try:
        interval = input("Logging interval in seconds (default 60): ")
        interval = int(interval) if interval else 60
    except (ValueError, EOFError):
        interval = 60
    
    await logger.run_logger(interval=interval)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")