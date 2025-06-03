#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()
email = os.getenv('SOLAR_ASSISTANT_EMAIL')
password = os.getenv('SOLAR_ASSISTANT_PASSWORD')

# Create session
session = requests.Session()

# Get login page to fetch CSRF token
login_page = session.get('https://solar-assistant.io/sign_in')

# Try to find CSRF token in the response
import re
csrf_match = re.search(r'name="_csrf_token"\s+type="hidden"\s+hidden\s+value="([^"]+)"', login_page.text)
if not csrf_match:
    csrf_match = re.search(r'name="csrf-token"\s+content="([^"]+)"', login_page.text)

if csrf_match:
    csrf_token = csrf_match.group(1)
    print(f"Found CSRF token: {csrf_token[:20]}...")
else:
    print("Could not find CSRF token")
    csrf_token = None

# Attempt login
login_data = {
    'user[email]': email,
    'user[password]': password,
    'user[remember_me]': 'true',
    '_csrf_token': csrf_token
}

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://solar-assistant.io/sign_in',
    'Origin': 'https://solar-assistant.io',
    'Content-Type': 'application/x-www-form-urlencoded'
}

print("Attempting login...")
login_response = session.post('https://solar-assistant.io/sign_in', 
                             data=login_data, 
                             headers=headers,
                             allow_redirects=True)

print(f"Login response status: {login_response.status_code}")
print(f"Final URL: {login_response.url}")

# Check if login was successful
if 'sign_out' in login_response.text or 'dashboard' in login_response.url:
    print("Login appears successful!")
    
    # Try to download the image
    print("Attempting to download image...")
    download_url = 'https://solar-assistant.io/sites/download/release?arch=rpi64'
    
    download_response = session.get(download_url, 
                                   headers=headers,
                                   stream=True,
                                   allow_redirects=True)
    
    print(f"Download response status: {download_response.status_code}")
    print(f"Content-Type: {download_response.headers.get('Content-Type', 'Unknown')}")
    
    # Check if we got an actual image file
    content_type = download_response.headers.get('Content-Type', '')
    if 'application/octet-stream' in content_type or 'application/x-gzip' in content_type or 'application/zip' in content_type or download_response.headers.get('Content-Disposition'):
        filename = 'solar-assistant-rpi64.img'
        
        # Try to get filename from Content-Disposition header
        if 'Content-Disposition' in download_response.headers:
            cd = download_response.headers['Content-Disposition']
            filename_match = re.search(r'filename="?([^"]+)"?', cd)
            if filename_match:
                filename = filename_match.group(1)
        
        print(f"Saving as: {filename}")
        with open(filename, 'wb') as f:
            for chunk in download_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Download complete! File saved as {filename}")
        print(f"File size: {os.path.getsize(filename) / (1024*1024):.2f} MB")
    else:
        print("Downloaded content doesn't appear to be the image file")
        print("First 500 chars of response:")
        print(download_response.text[:500])
else:
    print("Login failed!")
    print("First 500 chars of response:")
    print(login_response.text[:500])