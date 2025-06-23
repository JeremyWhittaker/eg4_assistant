#!/usr/bin/env python3
"""Find SRP login page and form"""

import asyncio
from playwright.async_api import async_playwright

async def find_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        urls_to_try = [
            'https://myaccount.srpnet.com',
            'https://myaccount.srpnet.com/login',
            'https://myaccount.srpnet.com/signin',
            'https://myaccount.srpnet.com/sts/Login',
            'https://www.srpnet.com/login',
            'https://myaccount.srpnet.com/power',
            'https://myaccount.srpnet.com/account/login'
        ]
        
        for url in urls_to_try:
            try:
                print(f"\nTrying: {url}")
                response = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                status = response.status if response else 'No response'
                final_url = page.url
                title = await page.title()
                
                print(f"  Status: {status}")
                print(f"  Final URL: {final_url}")
                print(f"  Title: {title}")
                
                # Look for login forms
                forms = await page.query_selector_all('form')
                print(f"  Forms found: {len(forms)}")
                
                # Look for username/email inputs
                username_inputs = await page.query_selector_all('input[type="email"], input[type="text"], input[name*="user"], input[name*="email"], input[id*="user"], input[id*="email"]')
                print(f"  Username inputs found: {len(username_inputs)}")
                
                # Look for password inputs
                password_inputs = await page.query_selector_all('input[type="password"]')
                print(f"  Password inputs found: {len(password_inputs)}")
                
                # Look for login buttons
                login_buttons = await page.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("Log"), button:has-text("Sign")')
                print(f"  Login buttons found: {len(login_buttons)}")
                
                # If we found a form with username and password, investigate further
                if username_inputs and password_inputs:
                    print("  *** Potential login page found! ***")
                    
                    # Get more details
                    for i, inp in enumerate(username_inputs[:2]):
                        attrs = await inp.evaluate("""
                            el => ({
                                name: el.name,
                                id: el.id,
                                type: el.type,
                                placeholder: el.placeholder
                            })
                        """)
                        print(f"    Username input {i}: {attrs}")
                    
                    for i, inp in enumerate(password_inputs[:2]):
                        attrs = await inp.evaluate("""
                            el => ({
                                name: el.name,
                                id: el.id,
                                type: el.type,
                                placeholder: el.placeholder
                            })
                        """)
                        print(f"    Password input {i}: {attrs}")
                        
                    await page.screenshot(path=f'srp_login_found_{url.replace("https://", "").replace("/", "_")}.png')
                    
            except Exception as e:
                print(f"  Error: {e}")
        
        await browser.close()

asyncio.run(find_login())