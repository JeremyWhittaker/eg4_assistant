#!/usr/bin/env python3
"""Final SRP test with correct selectors"""

import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

async def test_srp():
    # Get credentials
    username = os.getenv('SRP_USERNAME', '').strip().strip("'\"")
    password = os.getenv('SRP_PASSWORD', '').strip().strip("'\"")
    
    print(f"Testing with username: {username}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Go to main page
            print("Going to SRP main page...")
            await page.goto('https://myaccount.srpnet.com', wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Take screenshot
            await page.screenshot(path='srp_test_1_main.png')
            print("Screenshot saved: srp_test_1_main.png")
            
            # Fill login form
            try:
                # Fill username
                username_field = await page.wait_for_selector('input[name="username"]', timeout=10000)
                await username_field.fill(username)
                print("Filled username")
                
                # Fill password
                password_field = await page.query_selector('input[name="password"]')
                await password_field.fill(password)
                print("Filled password")
                
                # Take screenshot before login
                await page.screenshot(path='srp_test_2_filled.png')
                print("Screenshot saved: srp_test_2_filled.png")
                
                # Submit form
                await page.press('input[name="password"]', 'Enter')
                print("Submitted form")
                
                # Wait for navigation
                print("Waiting for login to complete...")
                await asyncio.sleep(5)
                
                # Take screenshot after login
                await page.screenshot(path='srp_test_3_after_login.png')
                current_url = page.url
                print(f"After login URL: {current_url}")
                
                # Try to navigate to dashboard
                print("Navigating to dashboard...")
                await page.goto('https://myaccount.srpnet.com/power/MyAccount/Dashboard', wait_until='networkidle')
                await asyncio.sleep(3)
                
                # Take final screenshot
                await page.screenshot(path='srp_test_4_dashboard.png', full_page=True)
                final_url = page.url
                print(f"Final URL: {final_url}")
                
                # Look for demand data
                if 'Dashboard' in final_url:
                    print("Successfully reached dashboard!")
                    
                    # Extract page content to find selectors
                    demand_data = await page.evaluate("""
                        () => {
                            const results = {
                                found: false,
                                selectors: [],
                                data: {}
                            };
                            
                            // Look for elements containing demand/peak
                            const allElements = document.querySelectorAll('*');
                            for (const elem of allElements) {
                                const text = (elem.textContent || '').toLowerCase();
                                if ((text.includes('demand') || text.includes('peak')) && 
                                    text.includes('kw') && 
                                    elem.children.length < 10) {
                                    
                                    results.selectors.push({
                                        tag: elem.tagName,
                                        class: elem.className,
                                        id: elem.id,
                                        text: elem.textContent.substring(0, 200)
                                    });
                                }
                            }
                            
                            // Try specific selectors based on the HTML you provided
                            const cardDetails = document.querySelector('.srp-card-details');
                            if (cardDetails) {
                                results.found = true;
                                results.data.cardContent = cardDetails.textContent;
                            }
                            
                            // Look for kW values
                            const kwRegex = /(\d+\.?\d*)\s*kW/gi;
                            const bodyText = document.body.textContent;
                            const kwMatches = bodyText.match(kwRegex);
                            if (kwMatches) {
                                results.data.kwValues = kwMatches.slice(0, 5);
                            }
                            
                            return results;
                        }
                    """)
                    
                    print("\nDemand data extraction:")
                    print(f"Found card: {demand_data['found']}")
                    if demand_data['data'].get('kwValues'):
                        print(f"kW values found: {demand_data['data']['kwValues']}")
                    
                    print(f"\nPotential selectors ({len(demand_data['selectors'])} found):")
                    for sel in demand_data['selectors'][:5]:
                        print(f"  {sel['tag']}.{sel['class']} - {sel['text'][:100]}...")
                    
            except Exception as e:
                print(f"Login error: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

asyncio.run(test_srp())