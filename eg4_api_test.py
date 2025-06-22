#!/usr/bin/env python3
"""
Test EG4 API endpoints directly
"""

import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def test_api():
    username = os.getenv('EG4_MONITOR_USERNAME')
    password = os.getenv('EG4_MONITOR_PASSWORD')
    base_url = 'https://monitor.eg4electronics.com'
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        # Login
        print("Logging in...")
        await page.goto(f"{base_url}/WManage/web/login")
        await page.fill('input[name="account"]', username)
        await page.fill('input[name="password"]', password)
        await page.press('input[name="password"]', 'Enter')
        await page.wait_for_load_state('networkidle')
        
        print("Login successful!")
        
        # Test 1: Get inverter list
        print("\nTest 1: Getting inverter list...")
        response = await page.request.get(f"{base_url}/WManage/web/config/inverter/list")
        if response.ok:
            data = await response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            if data.get('rows'):
                inverter_id = data['rows'][0]['id']
                print(f"\nFound inverter ID: {inverter_id}")
                
                # Test 2: Get realtime data
                print("\nTest 2: Getting realtime data...")
                response2 = await page.request.post(
                    f"{base_url}/WManage/web/monitor/inverter/getRealtimeData",
                    data={'inverterId': str(inverter_id)}
                )
                if response2.ok:
                    data2 = await response2.json()
                    print(f"Realtime data: {json.dumps(data2, indent=2)}")
                else:
                    print(f"Failed to get realtime data: {response2.status}")
                    
                # Test 3: Navigate with inverter ID
                print("\nTest 3: Navigating to inverter page...")
                await page.goto(f"{base_url}/WManage/web/monitor/inverter?inverterId={inverter_id}")
                await asyncio.sleep(5)
                
                # Check page content
                soc = await page.evaluate("() => document.querySelector('.socText')?.textContent")
                print(f"SOC from page: {soc}")
        else:
            print(f"Failed to get inverter list: {response.status}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_api())