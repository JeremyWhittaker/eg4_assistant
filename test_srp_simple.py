#!/usr/bin/env python3
"""Simple SRP test"""

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
        page = await browser.new_page()
        
        try:
            # Go directly to login page
            print("Going to SRP login...")
            response = await page.goto('https://myaccount.srpnet.com/sts/sign-in', wait_until='domcontentloaded', timeout=30000)
            print(f"Response status: {response.status if response else 'No response'}")
            print(f"URL: {page.url}")
            
            # Wait a bit
            await asyncio.sleep(3)
            
            # Check page title
            title = await page.title()
            print(f"Page title: {title}")
            
            # Look for login fields
            try:
                # Try to find username field
                username_field = await page.wait_for_selector('input[type="email"], input[name="username"], input[id*="username"], input[placeholder*="email"]', timeout=5000)
                if username_field:
                    print("Found username field!")
                    await username_field.fill(username)
                    
                    # Find password
                    password_field = await page.query_selector('input[type="password"]')
                    if password_field:
                        print("Found password field!")
                        await password_field.fill(password)
                        
                        # Submit
                        await page.keyboard.press('Enter')
                        print("Submitted login form")
                        
                        # Wait for navigation
                        await asyncio.sleep(5)
                        print(f"After login URL: {page.url}")
                        
                        # Try to go to dashboard
                        await page.goto('https://myaccount.srpnet.com/power/MyAccount/Dashboard', wait_until='domcontentloaded')
                        await asyncio.sleep(3)
                        
                        # Check if we made it
                        final_url = page.url
                        print(f"Final URL: {final_url}")
                        
                        if 'dashboard' in final_url.lower():
                            print("Successfully reached dashboard!")
                            
                            # Look for demand info
                            content = await page.content()
                            if 'demand' in content.lower():
                                print("Found 'demand' in page content")
                            if 'peak' in content.lower():
                                print("Found 'peak' in page content")
                            if 'kw' in content.lower():
                                print("Found 'kw' in page content")
                                
            except Exception as e:
                print(f"Login process error: {e}")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

asyncio.run(test_srp())