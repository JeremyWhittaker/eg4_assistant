#!/usr/bin/env python3
"""
Analyze Solar Assistant WebSocket/Phoenix LiveView connections
"""

import re
import json

def analyze_phoenix_liveview():
    """Extract Phoenix LiveView data from HTML pages"""
    
    pages = ['sa_page__.html', 'sa_page__power.html', 'sa_page__totals.html']
    results = {}
    
    for page in pages:
        try:
            with open(page, 'r') as f:
                content = f.read()
                
            # Find Phoenix session data
            session_match = re.search(r'data-phx-session="([^"]+)"', content)
            static_match = re.search(r'data-phx-static="([^"]+)"', content)
            main_match = re.search(r'data-phx-main\s+data-phx-session', content)
            
            # Find WebSocket endpoint
            ws_match = re.search(r'ws://[^"]+|wss://[^"]+', content)
            
            # Find LiveView routes
            lv_routes = re.findall(r'phx-[a-z-]+="([^"]+)"', content)
            
            # Find data attributes
            data_attrs = re.findall(r'data-[a-z-]+="([^"]+)"', content)
            
            results[page] = {
                'has_phoenix_session': bool(session_match),
                'has_liveview': bool(main_match),
                'routes': list(set(lv_routes)),
                'websocket': ws_match.group() if ws_match else None
            }
            
            print(f"\n{page}:")
            print(f"  Phoenix LiveView: {'Yes' if main_match else 'No'}")
            print(f"  Session Token: {'Found' if session_match else 'Not found'}")
            if lv_routes:
                print(f"  LiveView routes: {', '.join(set(lv_routes)[:5])}")
                
        except Exception as e:
            print(f"Error analyzing {page}: {e}")
    
    return results

if __name__ == "__main__":
    print("Analyzing Solar Assistant WebSocket/LiveView connections")
    print("=" * 60)
    analyze_phoenix_liveview()