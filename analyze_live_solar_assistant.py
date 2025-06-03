#!/usr/bin/env python3
"""
Analyze live Solar Assistant instance to understand its structure and data
"""

import requests
import json
from bs4 import BeautifulSoup
import time

SOLAR_ASSISTANT_IP = "172.16.106.13"

def analyze_solar_assistant():
    """Analyze the live Solar Assistant instance"""
    
    pages = [
        "/",
        "/#charts", 
        "/totals",
        "/power",
        "/configuration",
        "/api/status",
        "/api/data",
        "/api/inverter",
        "/api/totals",
        "/api/power",
        "/api/configuration"
    ]
    
    results = {}
    
    print(f"Analyzing Solar Assistant at http://{SOLAR_ASSISTANT_IP}")
    print("=" * 60)
    
    session = requests.Session()
    
    for page in pages:
        url = f"http://{SOLAR_ASSISTANT_IP}{page}"
        print(f"\nAnalyzing: {page}")
        
        try:
            response = session.get(url, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            
            results[page] = {
                'status': response.status_code,
                'content_type': response.headers.get('Content-Type', ''),
                'headers': dict(response.headers),
                'size': len(response.content)
            }
            
            # If it's HTML, parse it
            if 'text/html' in response.headers.get('Content-Type', ''):
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Find JavaScript files
                scripts = soup.find_all('script', src=True)
                results[page]['scripts'] = [s.get('src') for s in scripts]
                
                # Find API calls in inline scripts
                inline_scripts = soup.find_all('script', src=False)
                api_calls = []
                for script in inline_scripts:
                    if script.string:
                        # Look for fetch/ajax calls
                        if 'fetch(' in script.string or 'ajax' in script.string:
                            api_calls.append(script.string[:200])
                
                results[page]['api_calls'] = api_calls
                
                # Save sample HTML
                with open(f'sa_page_{page.replace("/", "_")}.html', 'w') as f:
                    f.write(response.text)
                    
            # If it's JSON, save it
            elif 'application/json' in response.headers.get('Content-Type', ''):
                try:
                    data = response.json()
                    results[page]['json_data'] = data
                    
                    with open(f'sa_data_{page.replace("/", "_")}.json', 'w') as f:
                        json.dump(data, f, indent=2)
                        
                except:
                    pass
                    
        except Exception as e:
            print(f"  Error: {e}")
            results[page] = {'error': str(e)}
    
    # Save results
    with open('solar_assistant_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n\nAnalysis complete. Results saved to solar_assistant_analysis.json")
    
    return results

if __name__ == "__main__":
    analyze_solar_assistant()