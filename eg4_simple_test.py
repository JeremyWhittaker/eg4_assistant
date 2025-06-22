#!/usr/bin/env python3
"""
Simple test to diagnose EG4 data loading issue
"""

import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    username = os.getenv('EG4_MONITOR_USERNAME') 
    password = os.getenv('EG4_MONITOR_PASSWORD')
    
    print("Starting browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        # Login
        print("Logging in...")
        await page.goto('https://monitor.eg4electronics.com/WManage/web/login')
        await page.fill('input[name="account"]', username)
        await page.fill('input[name="password"]', password)
        await page.press('input[name="password"]', 'Enter')
        await page.wait_for_load_state('networkidle')
        print("Login successful!")
        
        # Navigate to monitor
        print("Navigating to monitor page...")
        await page.goto('https://monitor.eg4electronics.com/WManage/web/monitor/inverter')
        
        # Wait and check data multiple times
        for i in range(30):
            await asyncio.sleep(1)
            
            # Check SOC
            soc = await page.evaluate("() => document.querySelector('.socText')?.textContent")
            battery_power = await page.evaluate("() => document.querySelector('.batteryPowerText')?.textContent")
            pv_power = await page.evaluate("() => document.querySelector('.pv1PowerText')?.textContent")
            
            print(f"Attempt {i+1}: SOC={soc}, Battery={battery_power}W, PV1={pv_power}W")
            
            if soc and soc != '--':
                print(f"\nSuccess! Data loaded:")
                print(f"  SOC: {soc}%")
                print(f"  Battery Power: {battery_power} W")
                print(f"  PV1 Power: {pv_power} W")
                
                # Get more data
                data = await page.evaluate("""
                    () => {
                        return {
                            grid_power: document.querySelector('.gridPowerText')?.textContent,
                            load_power: document.querySelector('.consumptionPowerText')?.textContent,
                            today_yield: document.querySelector('#todayYieldingText')?.textContent,
                            inverter_status: document.querySelector('.statusText')?.textContent
                        }
                    }
                """)
                
                print(f"  Grid Power: {data['grid_power']} W")
                print(f"  Load Power: {data['load_power']} W")
                print(f"  Today Yield: {data['today_yield']} kWh")
                print(f"  Status: {data['inverter_status']}")
                break
        else:
            print("\nFailed to load data after 30 attempts")
            
            # Take screenshot for debugging
            await page.screenshot(path='eg4_test_screenshot.png')
            print("Screenshot saved to eg4_test_screenshot.png")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())