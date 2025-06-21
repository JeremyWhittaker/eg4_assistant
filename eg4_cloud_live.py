#!/usr/bin/env python3
"""
EG4 Cloud Live Monitor - Continuously monitor battery SOC and other stats
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

class EG4CloudLive:
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
            
            # Wait for login form
            await self.page.wait_for_selector('input[name="account"]', timeout=10000)
            
            # Fill in credentials
            await self.page.fill('input[name="account"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            
            # Submit form
            await self.page.press('input[name="password"]', 'Enter')
            
            # Wait for navigation
            await self.page.wait_for_load_state('networkidle')
            
            # Check if login successful
            if 'login' not in self.page.url:
                return True
            return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def get_live_stats(self):
        """Get all live statistics from the monitor page"""
        try:
            # Navigate to monitor page if not already there
            if '/monitor/inverter' not in self.page.url:
                await self.page.goto(f"{self.base_url}/WManage/web/monitor/inverter", wait_until='networkidle')
                await asyncio.sleep(2)  # Wait for dynamic content
            
            # Extract data using JavaScript
            data = await self.page.evaluate("""
                () => {
                    let stats = {};
                    
                    // Battery SOC
                    let socElement = document.querySelector('.socText');
                    if (socElement) {
                        stats.battery_soc = parseInt(socElement.textContent);
                    } else {
                        let socHolder = document.querySelector('.socHolder');
                        if (socHolder) {
                            let match = socHolder.textContent.match(/(\\d+)%/);
                            if (match) stats.battery_soc = parseInt(match[1]);
                        }
                    }
                    
                    // Try to find other data elements
                    // Look for elements with class names containing power/voltage data
                    document.querySelectorAll('[class*="monitor"], [class*="data"], [class*="value"]').forEach(el => {
                        let text = el.textContent.trim();
                        let parent = el.parentElement;
                        
                        // Try to identify what this value represents
                        if (parent && parent.textContent) {
                            let label = parent.textContent.toLowerCase();
                            
                            // Extract numeric values
                            let numMatch = text.match(/-?\\d+\\.?\\d*/);
                            if (numMatch) {
                                let value = parseFloat(numMatch[0]);
                                
                                if (label.includes('battery') && label.includes('voltage')) {
                                    stats.battery_voltage = value;
                                } else if (label.includes('battery') && label.includes('power')) {
                                    stats.battery_power = value;
                                } else if (label.includes('grid') && label.includes('power')) {
                                    stats.grid_power = value;
                                } else if (label.includes('grid') && label.includes('voltage')) {
                                    stats.grid_voltage = value;
                                } else if ((label.includes('pv') || label.includes('solar')) && label.includes('power')) {
                                    stats.pv_power = value;
                                } else if (label.includes('load') && label.includes('power')) {
                                    stats.load_power = value;
                                }
                            }
                        }
                    });
                    
                    // Also check for global JavaScript variables
                    if (window.inverterData) {
                        Object.assign(stats, window.inverterData);
                    }
                    if (window.realtimeData) {
                        Object.assign(stats, window.realtimeData);
                    }
                    
                    return stats;
                }
            """)
            
            return data
            
        except Exception as e:
            print(f"Error getting live stats: {e}")
            return None
    
    async def display_stats(self, data):
        """Display the statistics"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if not data:
            print(f"[{timestamp}] No data available")
            return
            
        # Build display string
        display_parts = []
        
        if 'battery_soc' in data:
            display_parts.append(f"SOC: {data['battery_soc']}%")
            
        if 'battery_voltage' in data:
            display_parts.append(f"Batt V: {data['battery_voltage']:.1f}V")
            
        if 'battery_power' in data:
            bp = data['battery_power']
            display_parts.append(f"Batt: {bp:+.0f}W")
            
        if 'grid_power' in data:
            gp = data['grid_power']
            display_parts.append(f"Grid: {gp:+.0f}W")
            
        if 'pv_power' in data:
            display_parts.append(f"PV: {data['pv_power']:.0f}W")
            
        if 'load_power' in data:
            display_parts.append(f"Load: {data['load_power']:.0f}W")
        
        # Display on one line
        if display_parts:
            print(f"[{timestamp}] {' | '.join(display_parts)}")
        else:
            print(f"[{timestamp}] Data retrieved but no values found")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
    
    async def run_continuous(self, interval=30):
        """Run continuous monitoring"""
        await self.start(headless=True)
        
        try:
            print("Logging into EG4 cloud monitor...")
            if not await self.login():
                print("Login failed")
                return
                
            print("Login successful!")
            print(f"\nMonitoring live statistics every {interval} seconds")
            print("Press Ctrl+C to stop\n")
            
            # Initial fetch
            data = await self.get_live_stats()
            await self.display_stats(data)
            
            while True:
                try:
                    await asyncio.sleep(interval)
                    
                    # Refresh the page periodically to avoid timeout
                    if datetime.now().minute % 10 == 0 and datetime.now().second < interval:
                        print("Refreshing page...")
                        await self.page.reload(wait_until='networkidle')
                        await asyncio.sleep(2)
                    
                    data = await self.get_live_stats()
                    await self.display_stats(data)
                    
                except KeyboardInterrupt:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await self.close()

async def main():
    """Main function"""
    print("EG4 Cloud Live Monitor")
    print("="*50)
    print(f"Monitoring: {os.getenv('EG4_MONITOR_USERNAME')}")
    print()
    
    monitor = EG4CloudLive()
    await monitor.run_continuous(interval=30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")