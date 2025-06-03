#!/usr/bin/env python3
"""
Analyze EG4 web interface for API endpoints
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from dotenv import load_dotenv
import os

load_dotenv()

EG4_IP = os.getenv('EG4_IP', '172.16.107.53')
EG4_USERNAME = os.getenv('EG4_USERNAME', 'admin')
EG4_PASSWORD = os.getenv('EG4_PASSWORD', 'admin')

def analyze_web_interface():
    """Analyze the EG4 web interface for API endpoints"""
    
    session = requests.Session()
    session.auth = (EG4_USERNAME, EG4_PASSWORD)
    
    print(f"Analyzing EG4 web interface at http://{EG4_IP}")
    print("=" * 50)
    
    # Get the main page
    try:
        response = session.get(f"http://{EG4_IP}/index_en.html", timeout=10)
        print(f"Main page status: {response.status_code}")
        
        # Look for JavaScript files
        js_files = re.findall(r'src="([^"]+\.js)"', response.text)
        print(f"\nFound {len(js_files)} JavaScript files:")
        for js in js_files:
            print(f"  - {js}")
        
        # Look for API endpoints in the HTML
        api_patterns = [
            r'(api/[^"\']+)',
            r'(/cgi-bin/[^"\']+)',
            r'(ajax[^"\']+)',
            r'(json[^"\']+)',
            r'(data[^"\']+\.json)',
            r'(\.cgi[^"\']*)',
            r'(/get[^"\']+)',
            r'(/set[^"\']+)',
            r'(/status[^"\']+)',
        ]
        
        endpoints = set()
        for pattern in api_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            endpoints.update(matches)
        
        if endpoints:
            print(f"\nFound {len(endpoints)} potential API endpoints:")
            for endpoint in sorted(endpoints):
                print(f"  - {endpoint}")
        
        # Try common API endpoints
        common_endpoints = [
            '/api/status',
            '/api/data',
            '/api/inverter',
            '/api/realtime',
            '/cgi-bin/data.cgi',
            '/cgi-bin/status.cgi',
            '/status.json',
            '/data.json',
            '/inverter.json',
            '/realtime.json',
            '/get_data',
            '/get_status',
            '/ajax/status',
            '/ajax/data',
        ]
        
        print("\nTesting common API endpoints:")
        working_endpoints = []
        
        for endpoint in common_endpoints:
            try:
                url = f"http://{EG4_IP}{endpoint}"
                resp = session.get(url, timeout=3)
                if resp.status_code == 200:
                    print(f"  ✓ {endpoint} - Status {resp.status_code}")
                    working_endpoints.append({
                        'endpoint': endpoint,
                        'content_type': resp.headers.get('Content-Type', 'unknown'),
                        'size': len(resp.content),
                        'sample': resp.text[:200] if resp.text else None
                    })
                elif resp.status_code != 404:
                    print(f"  ? {endpoint} - Status {resp.status_code}")
            except:
                pass
        
        # Download and analyze JavaScript files
        print("\nAnalyzing JavaScript files for API calls:")
        for js_file in js_files[:5]:  # Analyze first 5 JS files
            try:
                if not js_file.startswith('http'):
                    js_url = f"http://{EG4_IP}/{js_file.lstrip('/')}"
                else:
                    js_url = js_file
                    
                js_resp = session.get(js_url, timeout=5)
                if js_resp.status_code == 200:
                    # Look for API calls in JavaScript
                    ajax_calls = re.findall(r'(ajax|fetch|XMLHttpRequest|\.get|\.post)[^;]+["\']([^"\']+)["\']', js_resp.text)
                    if ajax_calls:
                        print(f"\n  In {js_file}:")
                        for method, url in ajax_calls[:10]:
                            print(f"    - {method} -> {url}")
            except:
                pass
        
        # Save results
        results = {
            'main_page_url': f"http://{EG4_IP}/index_en.html",
            'javascript_files': js_files,
            'potential_endpoints': list(endpoints),
            'working_endpoints': working_endpoints,
        }
        
        with open('eg4_web_analysis.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n✓ Results saved to eg4_web_analysis.json")
        
        return results
        
    except Exception as e:
        print(f"Error analyzing web interface: {e}")
        return None

if __name__ == "__main__":
    analyze_web_interface()