#!/usr/bin/env python3
"""Debug SRP login and data extraction - Version 2"""

import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

async def debug_srp():
    # Get credentials and strip quotes
    username = os.getenv('SRP_USERNAME', '').strip().strip("'\"")
    password = os.getenv('SRP_PASSWORD', '').strip().strip("'\"")
    
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    
    try:
        # First go to the main SRP page
        print("\nNavigating to SRP main page...")
        await page.goto('https://myaccount.srpnet.com', wait_until='networkidle')
        await asyncio.sleep(2)
        
        # Take screenshot
        await page.screenshot(path='srp_main_page.png', full_page=True)
        print("Screenshot saved: srp_main_page.png")
        
        # Click on Sign in if needed
        try:
            sign_in_button = await page.query_selector('text="Sign in"')
            if sign_in_button:
                print("Clicking Sign in button...")
                await sign_in_button.click()
                await asyncio.sleep(2)
        except:
            pass
        
        # Now try to fill the login form
        print("\nLooking for login form...")
        
        # Try different selectors for username field
        username_selectors = [
            'input[name="UserName"]',
            'input[type="email"]',
            'input[placeholder*="email"]',
            'input[placeholder*="username"]',
            '#UserName',
            'input[id*="username"]',
            'input[id*="email"]'
        ]
        
        username_field = None
        for selector in username_selectors:
            try:
                username_field = await page.wait_for_selector(selector, timeout=5000)
                if username_field:
                    print(f"Found username field with selector: {selector}")
                    break
            except:
                continue
        
        if username_field:
            await username_field.fill(username)
            print("Filled username")
            
            # Find password field
            password_selectors = [
                'input[name="Password"]',
                'input[type="password"]',
                '#Password',
                'input[id*="password"]'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = await page.query_selector(selector)
                    if password_field:
                        print(f"Found password field with selector: {selector}")
                        break
                except:
                    continue
            
            if password_field:
                await password_field.fill(password)
                print("Filled password")
                
                # Take screenshot before login
                await page.screenshot(path='srp_before_login.png')
                print("Screenshot saved: srp_before_login.png")
                
                # Find and click login button
                login_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Log in")',
                    'button:has-text("Sign in")',
                    'input[type="submit"]',
                    'button[value="login"]'
                ]
                
                for selector in login_selectors:
                    try:
                        login_button = await page.query_selector(selector)
                        if login_button:
                            print(f"Clicking login button: {selector}")
                            await login_button.click()
                            break
                    except:
                        continue
                
                # Wait for navigation
                print("Waiting for login to complete...")
                await asyncio.sleep(5)
                
                # Take screenshot after login
                await page.screenshot(path='srp_after_login.png', full_page=True)
                print("Screenshot saved: srp_after_login.png")
                print(f"Current URL: {page.url}")
        
        # Now navigate to dashboard
        print("\nNavigating to dashboard...")
        await page.goto('https://myaccount.srpnet.com/power/MyAccount/Dashboard', wait_until='networkidle')
        await asyncio.sleep(5)
        
        # Take screenshot of dashboard
        await page.screenshot(path='srp_dashboard_final.png', full_page=True)
        print("Screenshot saved: srp_dashboard_final.png")
        print(f"Final URL: {page.url}")
        
        # Extract page content
        page_content = await page.content()
        
        # Save page content for analysis
        with open('srp_page_content.html', 'w') as f:
            f.write(page_content)
        print("Page content saved: srp_page_content.html")
        
        # Look for demand data with JavaScript
        print("\nExtracting demand data...")
        demand_data = await page.evaluate("""
            () => {
                const results = {
                    allText: document.body.innerText,
                    url: window.location.href,
                    title: document.title
                };
                
                // Look for elements containing peak or demand
                const elements = document.querySelectorAll('*');
                results.peakElements = [];
                results.demandElements = [];
                
                elements.forEach(elem => {
                    const text = elem.innerText || elem.textContent || '';
                    if (text.toLowerCase().includes('peak') && text.length < 500) {
                        results.peakElements.push({
                            tag: elem.tagName,
                            class: elem.className,
                            text: text.substring(0, 200)
                        });
                    }
                    if (text.toLowerCase().includes('demand') && text.length < 500) {
                        results.demandElements.push({
                            tag: elem.tagName,
                            class: elem.className,
                            text: text.substring(0, 200)
                        });
                    }
                });
                
                return results;
            }
        """)
        
        print(f"Page title: {demand_data['title']}")
        print(f"Page URL: {demand_data['url']}")
        print(f"\nFound {len(demand_data['peakElements'])} elements with 'peak'")
        for elem in demand_data['peakElements'][:5]:
            print(f"  {elem['tag']}.{elem['class']}: {elem['text'][:100]}...")
        
        print(f"\nFound {len(demand_data['demandElements'])} elements with 'demand'")
        for elem in demand_data['demandElements'][:5]:
            print(f"  {elem['tag']}.{elem['class']}: {elem['text'][:100]}...")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        await page.screenshot(path='srp_error.png')
        print("Error screenshot saved: srp_error.png")
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(debug_srp())