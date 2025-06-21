#!/usr/bin/env python3
"""
EG4 Battery SOC Monitor - Simple and focused
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

async def get_battery_soc():
    """Get battery SOC from EG4 cloud"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Login
            await page.goto('https://monitor.eg4electronics.com/WManage/web/login')
            await page.fill('input[name="account"]', os.getenv('EG4_MONITOR_USERNAME'))
            await page.fill('input[name="password"]', os.getenv('EG4_MONITOR_PASSWORD'))
            await page.press('input[name="password"]', 'Enter')
            await page.wait_for_load_state('networkidle')
            
            # Go to monitor page
            await page.goto('https://monitor.eg4electronics.com/WManage/web/monitor/inverter')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Get SOC
            soc = await page.evaluate("""
                () => {
                    let socElement = document.querySelector('.socText');
                    if (socElement) return parseInt(socElement.textContent);
                    
                    let socHolder = document.querySelector('.socHolder');
                    if (socHolder) {
                        let match = socHolder.textContent.match(/(\\d+)%/);
                        if (match) return parseInt(match[1]);
                    }
                    return null;
                }
            """)
            
            return soc
            
        finally:
            await browser.close()

async def main():
    """Monitor battery SOC continuously"""
    print("EG4 Battery SOC Monitor")
    print("="*40)
    print("Fetching battery SOC every 30 seconds")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            soc = await get_battery_soc()
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            if soc is not None:
                # Create a simple bar graph
                bar_length = 20
                filled = int(bar_length * soc / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                print(f"[{timestamp}] Battery: [{bar}] {soc}%")
            else:
                print(f"[{timestamp}] Error: Could not retrieve SOC")
                
            await asyncio.sleep(30)
            
        except KeyboardInterrupt:
            print("\nStopping monitor...")
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())