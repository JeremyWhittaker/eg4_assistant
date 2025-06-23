#!/usr/bin/env python3
import re
from bs4 import BeautifulSoup

def extract_liveview_data():
    """Extract LiveView data from the HTML"""
    
    with open('/home/jeremy/src/solar_assistant/docker/solar_assistant_main_page.html', 'r') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    print("=== Extracting Phoenix LiveView Data ===\n")
    
    # Find the main LiveView container
    main_div = soup.find('div', {'data-phx-main': True})
    if main_div:
        print(f"LiveView Session: {main_div.get('data-phx-session', 'N/A')[:50]}...")
        print(f"LiveView ID: {main_div.get('id', 'N/A')}")
    
    # Look for data in script tags
    print("\n=== Looking for data in script tags ===")
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and ('window.liveSocket' in script.string or 'phx' in script.string):
            print("Found LiveView script initialization")
            
    # Look for elements with specific classes or IDs
    print("\n=== Looking for data elements ===")
    
    # Find all divs with text content that might contain data
    all_text = soup.get_text()
    
    # Extract numbers with units
    patterns = [
        r'(\d+\.?\d*)\s*(kW|W|V|A|%|kWh|Wh)',
        r'Battery.*?(\d+)\s*%',
        r'Solar.*?(\d+\.?\d*)\s*kW',
        r'Grid.*?(\d+\.?\d*)\s*W',
        r'Load.*?(\d+\.?\d*)\s*W'
    ]
    
    print("\n=== Extracted Values ===")
    for pattern in patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        if matches:
            print(f"Pattern '{pattern}':")
            for match in matches[:10]:  # Limit to first 10 matches
                print(f"  {match}")
    
    # Look for specific div structures
    print("\n=== Looking for card/panel structures ===")
    cards = soup.find_all(['div', 'section'], class_=re.compile('card|panel|widget|stats'))
    print(f"Found {len(cards)} card-like elements")
    
    # Save a cleaner version of the HTML
    print("\n=== Saving cleaned HTML structure ===")
    with open('/home/jeremy/src/solar_assistant/docker/solar_assistant_structure.html', 'w') as f:
        f.write(soup.prettify())

if __name__ == "__main__":
    extract_liveview_data()