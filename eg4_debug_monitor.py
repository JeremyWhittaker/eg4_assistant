#!/usr/bin/env python3
"""
EG4 Debug Monitor - Debug why values aren't showing up
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class EG4DebugMonitor:
    def __init__(self):
        self.username = os.getenv('EG4_MONITOR_USERNAME')
        self.password = os.getenv('EG4_MONITOR_PASSWORD')
        self.base_url = 'https://monitor.eg4electronics.com'
        self.browser = None
        self.page = None
        
    async def start(self, headless=False):  # Set headless=False for debugging
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
    
    async def debug_page(self):
        """Debug what's on the page"""
        try:
            print("Navigating to monitor page...")
            await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
            
            # Wait longer for dynamic content
            print("Waiting for page to fully load...")
            await asyncio.sleep(5)
            
            # Take a screenshot
            await self.page.screenshot(path='eg4_debug_screenshot.png')
            print("Screenshot saved to eg4_debug_screenshot.png")
            
            # Check if we need to select a device first
            print("\n=== Checking for device selection ===")
            devices = await self.page.evaluate("""
                () => {
                    // Look for device list or selection
                    const selects = document.querySelectorAll('select');
                    const deviceInfo = [];
                    
                    selects.forEach(select => {
                        if (select.options.length > 0) {
                            deviceInfo.push({
                                id: select.id,
                                name: select.name,
                                options: Array.from(select.options).map(opt => ({
                                    text: opt.text,
                                    value: opt.value,
                                    selected: opt.selected
                                }))
                            });
                        }
                    });
                    
                    return deviceInfo;
                }
            """)
            
            if devices:
                print("Found device selectors:")
                for device in devices:
                    print(f"  {device}")
            
            # Check for any loading indicators
            print("\n=== Checking for loading indicators ===")
            loading = await self.page.evaluate("""
                () => {
                    const loadingElements = document.querySelectorAll('.loading, .spinner, [class*="load"]');
                    return loadingElements.length;
                }
            """)
            print(f"Found {loading} loading elements")
            
            # Try to find where the data actually is
            print("\n=== Searching for data elements ===")
            
            # Method 1: Check all elements with 'monitorDataText' class
            monitor_data = await self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('.monitorDataText');
                    const data = [];
                    
                    elements.forEach(elem => {
                        data.push({
                            class: elem.className,
                            id: elem.id,
                            text: elem.textContent,
                            parent_class: elem.parentElement?.className,
                            visible: elem.offsetParent !== null
                        });
                    });
                    
                    return data;
                }
            """)
            
            print(f"Found {len(monitor_data)} elements with monitorDataText class:")
            for item in monitor_data[:10]:  # Show first 10
                print(f"  Text: '{item['text']}', Visible: {item['visible']}, Classes: {item['class']}")
            
            # Method 2: Look for specific values we know should exist
            print("\n=== Looking for specific elements ===")
            specific_elements = await self.page.evaluate("""
                () => {
                    const searches = [
                        { selector: '.socText', name: 'SOC' },
                        { selector: '.batteryPowerText', name: 'Battery Power' },
                        { selector: '.pv1PowerText', name: 'PV1 Power' },
                        { selector: '.gridPowerText', name: 'Grid Power' },
                        { selector: '#todayYieldingText', name: 'Today Yield' }
                    ];
                    
                    const results = {};
                    
                    searches.forEach(search => {
                        const elem = document.querySelector(search.selector);
                        results[search.name] = {
                            found: elem !== null,
                            text: elem?.textContent || 'not found',
                            visible: elem?.offsetParent !== null,
                            innerHTML: elem?.innerHTML
                        };
                    });
                    
                    return results;
                }
            """)
            
            for name, info in specific_elements.items():
                print(f"{name}: Found={info['found']}, Text='{info['text']}', Visible={info.get('visible', 'N/A')}")
            
            # Method 3: Check for AJAX calls or WebSocket data
            print("\n=== Checking for data in JavaScript ===")
            js_data = await self.page.evaluate("""
                () => {
                    // Check for global data objects
                    const possibleVars = ['inverterData', 'monitorData', 'realtimeData', 'deviceData', 'window.inverterData'];
                    const foundData = {};
                    
                    possibleVars.forEach(varName => {
                        try {
                            const data = eval(varName);
                            if (data) {
                                foundData[varName] = typeof data === 'object' ? JSON.stringify(data).substring(0, 200) : data;
                            }
                        } catch (e) {}
                    });
                    
                    // Check localStorage
                    foundData.localStorage = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        if (key.includes('device') || key.includes('data')) {
                            foundData.localStorage[key] = localStorage.getItem(key)?.substring(0, 100);
                        }
                    }
                    
                    return foundData;
                }
            """)
            
            if js_data:
                print("Found JavaScript data:")
                print(js_data)
            
            # Method 4: Wait and check if data loads after delay
            print("\n=== Waiting 10 seconds for data to load ===")
            await asyncio.sleep(10)
            
            # Check SOC again
            soc_check = await self.page.evaluate("""
                () => {
                    const socElem = document.querySelector('.socText');
                    return {
                        found: socElem !== null,
                        text: socElem?.textContent,
                        innerHTML: socElem?.innerHTML,
                        parentHTML: socElem?.parentElement?.innerHTML
                    };
                }
            """)
            
            print(f"SOC after wait: {soc_check}")
            
            # Save page HTML for inspection
            html = await self.page.content()
            with open('eg4_debug_page.html', 'w') as f:
                f.write(html)
            print("\nPage HTML saved to eg4_debug_page.html")
            
        except Exception as e:
            print(f"Debug error: {e}")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()

async def main():
    """Main function"""
    print("EG4 Debug Monitor")
    print("="*60)
    
    monitor = EG4DebugMonitor()
    await monitor.start(headless=True)  # Run in headless mode
    
    try:
        print("Logging in...")
        if await monitor.login():
            print("Login successful!")
            await monitor.debug_page()
            
            print("\n\nDebug complete. Check:")
            print("1. eg4_debug_screenshot.png - Visual of the page")
            print("2. eg4_debug_page.html - Full HTML content")
            print("3. The output above for data findings")
            
            input("\nPress Enter to close browser...")
        else:
            print("Login failed!")
    finally:
        await monitor.close()

if __name__ == "__main__":
    asyncio.run(main())