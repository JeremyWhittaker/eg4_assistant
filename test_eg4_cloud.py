#!/usr/bin/env python3
"""Test EG4 cloud connection"""

import requests
from dotenv import load_dotenv
import os

load_dotenv()

username = os.getenv('EG4_MONITOR_USERNAME')
password = os.getenv('EG4_MONITOR_PASSWORD')

print(f"Testing connection to EG4 cloud monitor")
print(f"Username: {username}")
print(f"Password: {'*' * len(password) if password else 'NOT SET'}")

session = requests.Session()

# Test basic connectivity
try:
    print("\n1. Testing basic connectivity...")
    response = session.get('https://monitor.eg4electronics.com', timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Redirected to: {response.url}")
except Exception as e:
    print(f"   Error: {e}")

# Try to get login page
try:
    print("\n2. Getting login page...")
    response = session.get('https://monitor.eg4electronics.com/WManage/web/login', timeout=10)
    print(f"   Status: {response.status_code}")
    
    # Look for form fields
    if 'input' in response.text:
        print("   Found input fields")
        
        # Count form fields
        import re
        inputs = re.findall(r'<input[^>]+>', response.text)
        print(f"   Number of input fields: {len(inputs)}")
        
        # Look for field names
        for inp in inputs[:5]:
            name_match = re.search(r'name=["\']([^"\']+)', inp)
            type_match = re.search(r'type=["\']([^"\']+)', inp)
            if name_match:
                print(f"   Field: name='{name_match.group(1)}', type='{type_match.group(1) if type_match else 'text'}'")
                
except Exception as e:
    print(f"   Error: {e}")

# Check if we need cookies or tokens
print("\n3. Checking cookies...")
print(f"   Cookies: {session.cookies}")

print("\nNote: The website might require JavaScript. If so, use the Selenium version:")
print("python3 eg4_cloud_selenium.py")