#!/usr/bin/env python3
"""Debug SRP login and data extraction"""

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
    browser = await playwright.chromium.launch(headless=True)  # Run headless
    page = await browser.new_page()
    
    try:
        print("\nNavigating to SRP login page...")
        await page.goto('https://myaccount.srpnet.com/power/MyAccount/Dashboard', wait_until='networkidle')
        
        # Take screenshot of login page
        await page.screenshot(path='srp_login_page.png')
        print("Screenshot saved: srp_login_page.png")
        
        # Check if already logged in
        if 'Dashboard' in page.url and 'login' not in page.url.lower():
            print("Already logged in!")
        else:
            print("Need to login...")
            
            # Wait for login form
            await page.wait_for_selector('input[name="UserName"]', timeout=10000)
            
            # Fill credentials
            await page.fill('input[name="UserName"]', username)
            await page.fill('input[name="Password"]', password)
            
            # Take screenshot before login
            await page.screenshot(path='srp_before_login.png')
            print("Screenshot saved: srp_before_login.png")
            
            # Click login button
            await page.click('button[type="submit"]')
            
            # Wait for navigation
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # Take screenshot after login
            await page.screenshot(path='srp_after_login.png')
            print("Screenshot saved: srp_after_login.png")
            
            if 'Dashboard' in page.url:
                print("Login successful!")
            else:
                print(f"Login failed - current URL: {page.url}")
                return
        
        # Wait for dashboard to load
        print("\nWaiting for dashboard to load...")
        await page.wait_for_timeout(5000)
        
        # Take screenshot of dashboard
        await page.screenshot(path='srp_dashboard.png')
        print("Screenshot saved: srp_dashboard.png")
        
        # Try multiple selectors for the demand card
        selectors_to_try = [
            '.srp-card-details',
            '[class*="card-details"]',
            '.card',
            '[class*="demand"]',
            '.srp-red-text',
            '[class*="peak"]'
        ]
        
        print("\nSearching for demand data...")
        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"Found {len(elements)} elements matching '{selector}'")
                for i, elem in enumerate(elements[:3]):  # Check first 3
                    text = await elem.text_content()
                    print(f"  Element {i}: {text[:100] if text else 'No text'}")
        
        # Try to extract all text containing "kW" or "demand"
        print("\nSearching for kW values...")
        all_text = await page.content()
        import re
        kw_matches = re.findall(r'[\d.]+\s*kW', all_text, re.IGNORECASE)
        print(f"Found kW values: {kw_matches}")
        
        # Try JavaScript evaluation
        print("\nTrying JavaScript extraction...")
        demand_data = await page.evaluate("""
            () => {
                // Look for demand data in various ways
                const results = {
                    cards: [],
                    kwValues: [],
                    demandTexts: []
                };
                
                // Find all cards
                document.querySelectorAll('.card, [class*="card"]').forEach(card => {
                    const text = card.textContent || '';
                    if (text.toLowerCase().includes('demand') || text.includes('kW')) {
                        results.cards.push(text.trim().substring(0, 200));
                    }
                });
                
                // Find all kW values
                document.querySelectorAll('*').forEach(elem => {
                    const text = elem.textContent || '';
                    if (text.match(/\\d+\\.?\\d*\\s*kW/i) && !text.includes('<')) {
                        results.kwValues.push(text.trim());
                    }
                });
                
                // Find demand-related texts
                document.querySelectorAll('*').forEach(elem => {
                    const text = elem.textContent || '';
                    if (text.toLowerCase().includes('peak demand') && text.length < 200) {
                        results.demandTexts.push(text.trim());
                    }
                });
                
                return results;
            }
        """)
        
        print("JavaScript extraction results:")
        print(f"Cards found: {len(demand_data['cards'])}")
        for card in demand_data['cards'][:3]:
            print(f"  - {card[:100]}...")
        print(f"kW values: {demand_data['kwValues'][:10]}")
        print(f"Demand texts: {demand_data['demandTexts'][:5]}")
        
        # Wait before closing
        print("\nKeeping browser open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"Error: {e}")
        await page.screenshot(path='srp_error.png')
        print("Error screenshot saved: srp_error.png")
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(debug_srp())