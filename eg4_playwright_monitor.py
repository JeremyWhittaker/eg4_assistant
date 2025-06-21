#!/usr/bin/env python3
"""
EG4 Monitor using Playwright - Lightweight browser automation
First install: pip install playwright && playwright install chromium
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

class EG4PlaywrightMonitor:
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
            print("Opening login page...")
            await self.page.goto(f"{self.base_url}/WManage/web/login")
            
            # Wait for login form
            await self.page.wait_for_selector('input[name="account"]', timeout=10000)
            
            print(f"Logging in as {self.username}...")
            
            # Fill in credentials
            await self.page.fill('input[name="account"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            
            # Submit form
            await self.page.press('input[name="password"]', 'Enter')
            
            # Wait for navigation
            await self.page.wait_for_load_state('networkidle')
            
            # Check if login successful
            current_url = self.page.url
            if 'login' not in current_url:
                print("Login successful!")
                return True
            else:
                print("Login may have failed")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def get_battery_soc(self):
        """Get battery SOC from the monitor page"""
        try:
            # Navigate to monitor page
            monitor_url = f"{self.base_url}/WManage/web/monitor/inverter"
            print("Opening monitor page...")
            await self.page.goto(monitor_url)
            
            # Wait for data to load
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # Extra wait for dynamic content
            
            # Try multiple selectors
            selectors = [
                '.socText.monitorDataText',
                '.socText',
                '.socHolder',
                'p.socHolder strong',
                '[class*="soc"]',
                'text=/\\d+%/'  # Regex for any percentage
            ]
            
            for selector in selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        text = await element.text_content()
                        # Extract number from text
                        import re
                        match = re.search(r'(\d+)', text)
                        if match:
                            soc = int(match.group(1))
                            print(f"Found battery SOC: {soc}%")
                            return soc
                except:
                    continue
            
            # Try to execute JavaScript to get the value
            try:
                soc = await self.page.evaluate("""
                    () => {
                        // Look for SOC in various places
                        let socElement = document.querySelector('.socText');
                        if (socElement) return parseInt(socElement.textContent);
                        
                        // Try other selectors
                        let socHolder = document.querySelector('.socHolder');
                        if (socHolder) {
                            let match = socHolder.textContent.match(/(\d+)%/);
                            if (match) return parseInt(match[1]);
                        }
                        
                        // Look in global JavaScript variables
                        if (window.inverterData && window.inverterData.soc) {
                            return window.inverterData.soc;
                        }
                        
                        return null;
                    }
                """)
                
                if soc is not None:
                    print(f"Found battery SOC via JS: {soc}%")
                    return soc
                    
            except:
                pass
            
            print("Could not find battery SOC")
            
            # Save screenshot for debugging
            await self.page.screenshot(path='eg4_monitor_screenshot.png')
            print("Screenshot saved to eg4_monitor_screenshot.png")
            
            return None
            
        except Exception as e:
            print(f"Error getting battery SOC: {e}")
            return None
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
    
    async def run_once(self):
        """Run once and get battery SOC"""
        await self.start(headless=True)
        
        try:
            if await self.login():
                return await self.get_battery_soc()
        finally:
            await self.close()
            
        return None
    
    async def run_continuous(self, interval=30):
        """Run continuous monitoring"""
        await self.start(headless=True)
        
        try:
            if not await self.login():
                print("Login failed")
                return
                
            print(f"\nMonitoring battery SOC every {interval} seconds")
            print("Press Ctrl+C to stop\n")
            
            while True:
                try:
                    soc = await self.get_battery_soc()
                    
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    if soc is not None:
                        print(f"[{timestamp}] Battery SOC: {soc}%")
                    else:
                        print(f"[{timestamp}] Failed to get battery SOC")
                    
                    await asyncio.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        finally:
            await self.close()

async def main():
    """Main function"""
    print("EG4 Cloud Monitor using Playwright")
    print("="*50)
    
    monitor = EG4PlaywrightMonitor()
    
    # Test single fetch
    soc = await monitor.run_once()
    
    if soc is not None:
        print(f"\n✓ Successfully retrieved battery SOC: {soc}%")
        
        # Ask about continuous monitoring
        response = input("\nStart continuous monitoring? (y/n): ")
        if response.lower() == 'y':
            monitor = EG4PlaywrightMonitor()  # New instance for continuous
            await monitor.run_continuous(interval=30)
    else:
        print("\n✗ Failed to retrieve battery SOC")
        print("\nTo install Playwright:")
        print("pip install playwright")
        print("playwright install chromium")

if __name__ == "__main__":
    print("Note: This requires Playwright. Install with:")
    print("pip install playwright && playwright install chromium\n")
    
    try:
        asyncio.run(main())
    except ImportError:
        print("Playwright not installed. Installing...")
        os.system("pip install playwright")
        print("\nNow run: playwright install chromium")
        print("Then run this script again")