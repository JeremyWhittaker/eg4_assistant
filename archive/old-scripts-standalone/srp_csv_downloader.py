#!/usr/bin/env python3
"""
SRP CSV Downloader - Downloads energy usage data from SRP for all chart types
"""

import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

async def download_srp_csvs():
    """Download all CSV data types from SRP"""
    username = os.getenv('SRP_USERNAME', '')
    password = os.getenv('SRP_PASSWORD', '')
    
    if not username or not password:
        print("Error: SRP_USERNAME and SRP_PASSWORD environment variables are required")
        return None
    
    playwright = None
    browser = None
    
    # Chart types to download
    chart_types = {
        'net': 'Net energy',
        'generation': 'Generation', 
        'usage': 'Usage',
        'demand': 'Demand'
    }
    
    downloaded_files = {}
    
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
        
        # Download each chart type
        for chart_key, chart_name in chart_types.items():
            print(f"\n=== Downloading {chart_name} data ===")
            
            # Look for and click the chart type button/link
            chart_selector = f'button:has-text("{chart_name}"), a:has-text("{chart_name}"), [title*="{chart_name}"]'
            chart_button = await page.query_selector(chart_selector)
            
            if not chart_button:
                # Try alternative: look for the chart navigation
                chart_button = await page.query_selector(f'[data-chart-type="{chart_key}"], [data-view="{chart_key}"]')
            
            if chart_button:
                print(f"Found {chart_name} button, clicking...")
                await chart_button.click()
                await asyncio.sleep(2)  # Wait for chart to load
            else:
                print(f"Warning: Could not find {chart_name} button, trying to export anyway...")
            
            # Look for the Export to Excel button
            print(f"Looking for Export to Excel button for {chart_name}...")
            export_button = await page.query_selector('button:has-text("Export to Excel")')
            
            if not export_button:
                print(f"Export button not found for {chart_name}! Skipping...")
                continue
            
            print(f"Found Export to Excel button for {chart_name}, clicking...")
            
            try:
                # Start waiting for download before clicking
                async with page.expect_download(timeout=30000) as download_info:
                    await export_button.click()
                    print(f"Clicked export button for {chart_name}, waiting for download...")
                    download = await download_info.value
                
                # Save the download with chart type in filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'srp_{chart_key}_{timestamp}.csv'
                filepath = os.path.join(downloads_dir, filename)
                await download.save_as(filepath)
                
                downloaded_files[chart_key] = filepath
                print(f"{chart_name} file downloaded successfully: {filepath}")
                
                # Read and display first few lines
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    print(f"\nFirst 5 lines of {chart_name} CSV:")
                    for line in lines[:5]:
                        print(line.strip())
                
            except Exception as e:
                print(f"Failed to download {chart_name}: {e}")
                continue
            
            # Wait a bit before next download
            await asyncio.sleep(2)
        
        return downloaded_files
        
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
    print("SRP CSV Downloader - All Chart Types")
    print("-" * 50)
    
    result = await download_srp_csvs()
    
    if result:
        print(f"\n\nSuccess! Downloaded {len(result)} CSV files:")
        for chart_type, filepath in result.items():
            print(f"  {chart_type}: {filepath}")
    else:
        print("\nFailed to download CSV files")

if __name__ == "__main__":
    asyncio.run(main())