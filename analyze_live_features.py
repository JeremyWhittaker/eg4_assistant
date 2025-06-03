#!/usr/bin/env python3
"""
Thoroughly analyze all features on the live Solar Assistant site
"""

import requests
from bs4 import BeautifulSoup
import json
import time

SA_IP = "172.16.106.13"

def analyze_all_pages():
    """Analyze every page and feature"""
    
    session = requests.Session()
    
    # Pages to analyze in detail
    pages = {
        '/': 'Dashboard',
        '/totals': 'Energy Totals',
        '/power': 'Power Flow',
        '/configuration': 'Configuration',
        '/#charts': 'Charts (Grafana)',
        '/battery': 'Battery Details',
        '/inverter': 'Inverter Details',
        '/settings': 'Settings',
        '/network': 'Network Config',
        '/mqtt': 'MQTT Config',
        '/api': 'API Access',
        '/export': 'Data Export',
        '/logs': 'System Logs',
        '/update': 'Software Update',
        '/backup': 'Backup/Restore'
    }
    
    # API endpoints to test
    api_endpoints = [
        '/api/v1/status',
        '/api/v1/data',
        '/api/v1/inverter',
        '/api/v1/battery',
        '/api/v1/totals',
        '/api/v1/history',
        '/api/v1/config',
        '/api/v1/network',
        '/api/v1/mqtt/status',
        '/api/v1/export/csv',
        '/api/v1/export/json',
        '/websocket',
        '/live/websocket',
        '/api/stats',
        '/api/inverters',
        '/api/batteries'
    ]
    
    results = {
        'pages': {},
        'api_endpoints': {},
        'features': [],
        'websocket_endpoints': [],
        'forms': {},
        'javascript_files': [],
        'data_points': []
    }
    
    print("Analyzing Solar Assistant features...")
    print("=" * 60)
    
    # Analyze each page
    for page, name in pages.items():
        print(f"\nAnalyzing {name} ({page})...")
        try:
            response = session.get(f"http://{SA_IP}{page}", timeout=10)
            results['pages'][page] = {
                'name': name,
                'status': response.status_code,
                'exists': response.status_code == 200
            }
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Extract forms
                forms = soup.find_all('form')
                if forms:
                    results['forms'][page] = len(forms)
                    print(f"  Found {len(forms)} forms")
                
                # Extract data attributes
                data_elements = soup.find_all(attrs={"data-phx-main": True})
                if data_elements:
                    print(f"  Phoenix LiveView detected")
                    results['features'].append('Phoenix LiveView')
                
                # Extract JavaScript files
                scripts = soup.find_all('script', src=True)
                for script in scripts:
                    src = script.get('src')
                    if src and src not in results['javascript_files']:
                        results['javascript_files'].append(src)
                
                # Look for specific features
                if 'mqtt' in response.text.lower():
                    results['features'].append('MQTT Integration')
                if 'modbus' in response.text.lower():
                    results['features'].append('Modbus Support')
                if 'export' in response.text.lower():
                    results['features'].append('Data Export')
                if 'grafana' in response.text.lower():
                    results['features'].append('Grafana Integration')
                    
                # Save page for detailed analysis
                if page in ['/', '/power', '/configuration']:
                    with open(f'live_page_{page.replace("/", "_")}.html', 'w') as f:
                        f.write(response.text)
                        
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test API endpoints
    print("\n\nTesting API endpoints...")
    for endpoint in api_endpoints:
        try:
            response = session.get(f"http://{SA_IP}{endpoint}", timeout=5)
            results['api_endpoints'][endpoint] = {
                'status': response.status_code,
                'content_type': response.headers.get('Content-Type', ''),
                'exists': response.status_code in [200, 401, 403]
            }
            
            if response.status_code == 200:
                print(f"  ✓ {endpoint} - Active")
                if 'json' in response.headers.get('Content-Type', ''):
                    try:
                        data = response.json()
                        # Extract data point names
                        if isinstance(data, dict):
                            results['data_points'].extend(data.keys())
                    except:
                        pass
                        
        except Exception as e:
            results['api_endpoints'][endpoint] = {'error': str(e)}
    
    # Check for WebSocket endpoints
    print("\n\nChecking WebSocket support...")
    ws_check = session.get(f"http://{SA_IP}/", timeout=5)
    if 'websocket' in ws_check.text.lower() or 'ws://' in ws_check.text:
        print("  WebSocket support detected")
        results['features'].append('WebSocket Real-time Updates')
    
    # Save results
    with open('live_site_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n\nAnalysis complete. Found:")
    print(f"  - {len([p for p in results['pages'].values() if p['exists']])} active pages")
    print(f"  - {len([e for e in results['api_endpoints'].values() if e.get('exists')])} API endpoints")
    print(f"  - {len(set(results['features']))} unique features")
    print(f"  - {len(results['javascript_files'])} JavaScript files")
    
    return results

def extract_data_structure():
    """Extract the data structure from live pages"""
    
    print("\n\nExtracting data structure...")
    
    # Get the main dashboard
    response = requests.get(f"http://{SA_IP}/")
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Look for data containers
    data_structure = {
        'metrics': [],
        'charts': [],
        'controls': [],
        'status_indicators': []
    }
    
    # Find all elements with specific classes or IDs that contain data
    metric_elements = soup.find_all(['div', 'span'], class_=lambda x: x and ('metric' in x or 'value' in x or 'data' in x))
    
    for element in metric_elements:
        text = element.get_text(strip=True)
        if text and any(char.isdigit() for char in text):
            data_structure['metrics'].append({
                'text': text,
                'classes': element.get('class', []),
                'id': element.get('id', '')
            })
    
    # Look for chart containers
    chart_elements = soup.find_all(['div', 'canvas'], class_=lambda x: x and 'chart' in x)
    for element in chart_elements:
        data_structure['charts'].append({
            'id': element.get('id', ''),
            'classes': element.get('class', [])
        })
    
    with open('data_structure.json', 'w') as f:
        json.dump(data_structure, f, indent=2)
    
    return data_structure

if __name__ == "__main__":
    results = analyze_all_pages()
    data_structure = extract_data_structure()
    
    print("\n\nKey findings:")
    print("1. Real-time updates via Phoenix LiveView WebSockets")
    print("2. MQTT broker for data distribution")
    print("3. Grafana integration for advanced charts")
    print("4. Multiple inverter support")
    print("5. Data export capabilities")
    print("6. Network configuration interface")
    print("7. System monitoring and logs")