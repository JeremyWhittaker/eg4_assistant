#!/usr/bin/env python3
"""
EG4 Debug Scraper - To identify correct selectors
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

async def debug_scrape():
    """Debug function to find correct selectors"""
    username = os.getenv('EG4_MONITOR_USERNAME', '').strip().strip("'\"")
    password = os.getenv('EG4_MONITOR_PASSWORD', '').strip().strip("'\"")
    
    print(f"Using credentials: {username}")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        # Login
        print("Logging in...")
        await page.goto("https://monitor.eg4electronics.com/WManage/web/login", wait_until='networkidle')
        await page.wait_for_selector('input[name="account"]', timeout=10000)
        
        await page.fill('input[name="account"]', username)
        await page.fill('input[name="password"]', password)
        await page.press('input[name="password"]', 'Enter')
        
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        # Navigate to monitor
        print("Navigating to monitor page...")
        await page.goto("https://monitor.eg4electronics.com/WManage/web/monitor/inverter", wait_until='networkidle')
        await asyncio.sleep(3)
        
        # Try to click on inverter if needed
        try:
            inverter_selector = await page.query_selector('.inverter-item, [class*="inverter-card"]')
            if inverter_selector:
                print("Found inverter selector, clicking...")
                await inverter_selector.click()
                await asyncio.sleep(3)
        except:
            pass
        
        # Wait for data to load
        print("Waiting for data to load...")
        await asyncio.sleep(5)
        
        # Take a screenshot
        await page.screenshot(path='eg4_debug_screenshot.png')
        print("Screenshot saved as eg4_debug_screenshot.png")
        
        # Debug: Get all text elements with their selectors
        print("\n=== DEBUGGING SELECTORS ===")
        
        # Try to find all elements with text content
        elements_data = await page.evaluate("""
            () => {
                const results = [];
                
                // Find all elements with text
                const allElements = document.querySelectorAll('*');
                
                for (let elem of allElements) {
                    const text = elem.textContent?.trim();
                    if (text && text.length > 0 && text.length < 50 && elem.children.length === 0) {
                        // Get all classes
                        const classes = Array.from(elem.classList).join(' ');
                        const id = elem.id || '';
                        const tagName = elem.tagName.toLowerCase();
                        
                        // Check if it contains numeric data or units
                        if (text.match(/\\d+|kWh|W|V|Hz|°C|%/) || 
                            text.includes('Battery') || text.includes('Solar') || 
                            text.includes('Grid') || text.includes('Load')) {
                            
                            results.push({
                                text: text,
                                classes: classes,
                                id: id,
                                tag: tagName,
                                selector: elem.id ? `#${elem.id}` : (classes ? `.${classes.split(' ')[0]}` : tagName)
                            });
                        }
                    }
                }
                
                return results;
            }
        """)
        
        print("\nFound elements with potential data:")
        for elem in elements_data:
            print(f"Text: '{elem['text']}' | Selector: '{elem['selector']}' | Classes: '{elem['classes']}' | ID: '{elem['id']}'")
        
        # Try specific patterns
        print("\n=== CHECKING SPECIFIC PATTERNS ===")
        
        patterns = [
            "div[class*='battery']",
            "div[class*='soc']",
            "div[class*='power']",
            "div[class*='pv']",
            "div[class*='grid']",
            "div[class*='load']",
            "div[class*='consumption']",
            "span[class*='value']",
            "span[class*='text']",
            ".value",
            ".text",
            "[class*='Value']",
            "[class*='Text']"
        ]
        
        for pattern in patterns:
            elements = await page.query_selector_all(pattern)
            if elements:
                print(f"\nPattern '{pattern}' found {len(elements)} elements:")
                for i, elem in enumerate(elements[:5]):  # Show first 5
                    text = await elem.text_content()
                    if text and text.strip():
                        print(f"  [{i}] {text.strip()}")
        
        # Get page structure
        print("\n=== PAGE STRUCTURE ===")
        structure = await page.evaluate("""
            () => {
                const getStructure = (elem, depth = 0, maxDepth = 3) => {
                    if (depth > maxDepth) return '';
                    
                    const indent = '  '.repeat(depth);
                    let result = indent + elem.tagName;
                    
                    if (elem.id) result += `#${elem.id}`;
                    if (elem.className) result += `.${elem.className.split(' ')[0]}`;
                    
                    const text = elem.textContent?.trim();
                    if (text && text.length < 30 && elem.children.length === 0) {
                        result += ` -> "${text}"`;
                    }
                    
                    result += '\\n';
                    
                    for (let child of elem.children) {
                        if (child.tagName !== 'SCRIPT' && child.tagName !== 'STYLE') {
                            result += getStructure(child, depth + 1, maxDepth);
                        }
                    }
                    
                    return result;
                };
                
                const mainContent = document.querySelector('main') || 
                                   document.querySelector('[class*="main"]') || 
                                   document.querySelector('[class*="content"]') ||
                                   document.body;
                
                return getStructure(mainContent, 0, 4);
            }
        """)
        
        print(structure[:5000])  # First 5000 chars
        
        # Try to extract actual data with various selectors
        print("\n=== ATTEMPTING DATA EXTRACTION ===")
        
        test_data = await page.evaluate("""
            () => {
                const getText = (selector) => {
                    const elem = document.querySelector(selector);
                    return elem ? elem.textContent.trim() : null;
                };
                
                const getByPattern = (pattern) => {
                    const elems = document.querySelectorAll(`[class*="${pattern}"]`);
                    const results = [];
                    for (let elem of elems) {
                        const text = elem.textContent?.trim();
                        if (text) results.push(text);
                    }
                    return results;
                };
                
                return {
                    battery_patterns: getByPattern('battery'),
                    soc_patterns: getByPattern('soc'),
                    power_patterns: getByPattern('power'),
                    pv_patterns: getByPattern('pv'),
                    grid_patterns: getByPattern('grid'),
                    load_patterns: getByPattern('load'),
                    consumption_patterns: getByPattern('consumption'),
                    value_patterns: getByPattern('value'),
                    all_numbers: Array.from(document.querySelectorAll('*'))
                        .map(e => e.textContent?.trim())
                        .filter(t => t && t.match(/^\\d+[\\.\\d]*\\s*[kWVAHz%°C]*$/))
                        .slice(0, 50)
                };
            }
        """)
        
        print("\nPattern matches:")
        for key, values in test_data.items():
            if values and len(values) > 0:
                print(f"\n{key}:")
                for v in values[:10]:  # First 10
                    print(f"  - {v}")
        
        print("\n=== DONE ===")
        print("Check eg4_debug_screenshot.png to see what the page looks like")
        print("Compare the values shown in the screenshot with what we're extracting")
        
    except Exception as e:
        print(f"Error: {e}")
        await page.screenshot(path='eg4_error_screenshot.png')
        print("Error screenshot saved")
    
    finally:
        # input("\nPress Enter to close browser...")
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(debug_scrape())