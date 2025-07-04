#!/usr/bin/env python3
"""
SRP CSV Downloader - Downloads energy usage data from SRP
"""

import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

async def download_srp_csv():
    """Download CSV data from SRP"""
    username = os.getenv('SRP_USERNAME', '')
    password = os.getenv('SRP_PASSWORD', '')
    
    if not username or not password:
        print("Error: SRP_USERNAME and SRP_PASSWORD environment variables are required")
        return None
    
    playwright = None
    browser = None
    
    try:
        print("Starting browser...")
        playwright = await async_playwright().start()
        
        # Create downloads directory
        downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Launch browser with downloads path
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox'],
            downloads_path=downloads_dir
        )
        
        context = await browser.new_context(
            accept_downloads=True
        )
        page = await context.new_page()
        
        print("Navigating to SRP login page...")
        await page.goto('https://myaccount.srpnet.com/power', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # Check if already logged in
        if 'dashboard' not in page.url:
            print("Logging in...")
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.press('input[name="password"]', 'Enter')
            await asyncio.sleep(5)
            
            # Verify login
            if 'dashboard' not in page.url and 'myaccount' not in page.url:
                print("Login failed!")
                return None
        
        print("Login successful, navigating to usage page...")
        await page.goto('https://myaccount.srpnet.com/power/myaccount/usage', wait_until='networkidle')
        await asyncio.sleep(3)
        
        # Wait for the page to fully load
        print("Waiting for usage data to load...")
        await page.wait_for_selector('.srp-red-text strong', timeout=10000)
        
        # Look for the Export to Excel button
        print("Looking for Export to Excel button...")
        export_button = await page.query_selector('button.btn.srp-btn.btn-lightblue.text-white:has-text("Export to Excel")')
        
        if not export_button:
            # Try alternative selectors
            export_button = await page.query_selector('button:has-text("Export to Excel")')
        
        if not export_button:
            print("Export button not found! Let me check what's on the page...")
            # Debug: print all buttons
            buttons = await page.query_selector_all('button')
            print(f"Found {len(buttons)} buttons on page")
            for i, btn in enumerate(buttons):
                text = await btn.text_content()
                classes = await btn.get_attribute('class')
                print(f"Button {i}: '{text}' with classes: {classes}")
            return None
        
        print("Found Export to Excel button, clicking...")
        
        # Start waiting for download before clicking
        async with page.expect_download() as download_info:
            await export_button.click()
            print("Clicked export button, waiting for download...")
            download = await download_info.value
        
        # Save the download
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'srp_usage_{timestamp}.csv'
        filepath = os.path.join(downloads_dir, filename)
        await download.save_as(filepath)
        
        print(f"File downloaded successfully: {filepath}")
        
        # Read and print the CSV content
        with open(filepath, 'r') as f:
            content = f.read()
        
        print("\n=== CSV Content ===")
        print(content)
        print("=== End of CSV ===\n")
        
        return filepath
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

async def main():
    """Main function"""
    print("SRP CSV Downloader")
    print("-" * 50)
    
    result = await download_srp_csv()
    
    if result:
        print(f"\nSuccess! CSV saved to: {result}")
    else:
        print("\nFailed to download CSV")

if __name__ == "__main__":
    asyncio.run(main())