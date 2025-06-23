#!/usr/bin/env python3
"""Standalone SRP test that mimics the exact flow from eg4_web_monitor.py"""

import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

class SRPMonitor:
    def __init__(self, username=None, password=None):
        self.username = (username or os.getenv('SRP_USERNAME', '')).strip().strip("'\"")
        self.password = (password or os.getenv('SRP_PASSWORD', '')).strip().strip("'\"")
        self.base_url = 'https://myaccount.srpnet.com'
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def start(self):
        """Start the browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        
    async def login(self):
        """Login to SRP account"""
        try:
            print(f"Attempting SRP login with username: {self.username}")
            
            # Go to the main page which should redirect to login
            await self.page.goto(self.base_url, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Check if we're already logged in
            if 'MyAccount/Dashboard' in self.page.url:
                print("Already logged in to SRP")
                return True
            
            # Look for the login form
            try:
                # Try desktop username field first
                username_field = await self.page.wait_for_selector('input[name="username"], input#username_desktop', timeout=10000)
                await username_field.fill(self.username)
                print("Filled username")
                
                # Fill password
                password_field = await self.page.query_selector('input[name="password"], input#password_desktop')
                if password_field:
                    await password_field.fill(self.password)
                    print("Filled password")
                    
                    # Find and click the login button
                    login_button = await self.page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Log in")')
                    if login_button:
                        await login_button.click()
                        print("Clicked login button")
                    else:
                        # Try pressing Enter
                        await password_field.press('Enter')
                        print("Pressed Enter to submit")
                    
                    # Wait for navigation
                    await asyncio.sleep(5)
                    
                    # Now try to navigate to dashboard
                    await self.page.goto(f"{self.base_url}/power/MyAccount/Dashboard", wait_until='networkidle')
                    await asyncio.sleep(3)
                    
                    # Check if login successful
                    current_url = self.page.url
                    if 'Dashboard' in current_url or 'MyAccount' in current_url:
                        print("SRP login successful!")
                        return True
                    else:
                        print(f"SRP login failed - ended up at: {current_url}")
                        return False
                        
            except Exception as e:
                print(f"Login form error: {e}")
                return False
                
        except Exception as e:
            print(f"SRP login error: {e}")
            return False
    
    async def get_peak_demand(self):
        """Get peak demand data from SRP dashboard"""
        try:
            # Wait for page to stabilize
            await asyncio.sleep(2)
            
            # Extract peak demand value - more generic approach
            demand_data = await self.page.evaluate("""
                () => {
                    // Look for kW values in the page
                    const bodyText = document.body.textContent || '';
                    const kwRegex = /(\\d+\\.?\\d*)\\s*kW/gi;
                    const kwMatches = bodyText.match(kwRegex) || [];
                    
                    // Look for demand-related text
                    let demandValue = '--';
                    let demandType = 'PEAK DEMAND';
                    let cycleInfo = '';
                    
                    // Try to find card with demand info
                    const cards = document.querySelectorAll('.card, [class*="card"], .srp-card-details');
                    for (const card of cards) {
                        const cardText = card.textContent || '';
                        if (cardText.toLowerCase().includes('demand') || cardText.toLowerCase().includes('peak')) {
                            // Extract the first kW value from this card
                            const cardKwMatch = cardText.match(kwRegex);
                            if (cardKwMatch && cardKwMatch[0]) {
                                demandValue = cardKwMatch[0];
                            }
                            
                            // Look for cycle/billing info
                            if (cardText.includes('Billing cycle') || cardText.includes('cycle')) {
                                const cycleMatch = cardText.match(/Billing cycle[^.]+/i);
                                if (cycleMatch) {
                                    cycleInfo = cycleMatch[0];
                                }
                            }
                            
                            break;
                        }
                    }
                    
                    // If no card found, use the first kW value from the page
                    if (demandValue === '--' && kwMatches.length > 0) {
                        demandValue = kwMatches[0];
                    }
                    
                    return {
                        demand: demandValue,
                        type: demandType,
                        cycleInfo: cycleInfo,
                        timestamp: new Date().toISOString(),
                        allKwValues: kwMatches.slice(0, 5)  // For debugging
                    };
                }
            """)
            
            if demand_data:
                print(f"SRP demand extracted: {demand_data['demand']}")
                if demand_data.get('allKwValues'):
                    print(f"All kW values found: {demand_data['allKwValues']}")
            
            return demand_data
            
        except Exception as e:
            print(f"Error getting peak demand: {e}")
            return {'error': str(e), 'demand': '--', 'type': 'ERROR'}
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def test_srp():
    srp = SRPMonitor()
    try:
        await srp.start()
        login_success = await srp.login()
        if login_success:
            demand_data = await srp.get_peak_demand()
            print(f"\nFinal result: {demand_data}")
            return demand_data
        else:
            print("\nLogin failed!")
            return {'error': 'Failed to login to SRP'}
    except Exception as e:
        print(f"\nError: {e}")
        return {'error': str(e)}
    finally:
        await srp.close()

if __name__ == "__main__":
    result = asyncio.run(test_srp())
    print(f"\nTest complete. Result: {result}")