#!/usr/bin/env python3
import websocket
import json
import requests
import time
import threading

class SolarAssistantWebSocket:
    def __init__(self):
        self.base_url = "http://172.16.106.13"
        self.ws_url = "ws://172.16.106.13/live/websocket?vsn=2.0.0"
        self.session = requests.Session()
        self.ws = None
        self.running = True
        
    def get_session(self):
        """Get a session cookie by loading the main page"""
        response = self.session.get(f"{self.base_url}/")
        print(f"Got session cookie: {self.session.cookies.get('_solar_assistant_key', 'None')[:50]}...")
        
        # Extract CSRF token
        import re
        match = re.search(r'name="csrf-token" content="([^"]+)"', response.text)
        if match:
            self.csrf_token = match.group(1)
            print(f"CSRF Token: {self.csrf_token}")
        
        # Extract phx session from HTML
        match = re.search(r'data-phx-session="([^"]+)"', response.text)
        if match:
            self.phx_session = match.group(1)
            print(f"PHX Session: {self.phx_session[:50]}...")
            
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        print(f"\n[RECEIVED] {message}")
        
        # Try to parse as JSON array (Phoenix format)
        try:
            data = json.loads(message)
            if isinstance(data, list) and len(data) >= 5:
                join_ref, ref, topic, event, payload = data[:5]
                print(f"  Topic: {topic}")
                print(f"  Event: {event}")
                print(f"  Payload: {json.dumps(payload, indent=2)}")
                
                # If it's a diff event, show the changes
                if event == "phx_reply" and "diff" in str(payload):
                    print("  [LiveView Diff Detected]")
                    
        except json.JSONDecodeError:
            print("  [Not JSON]")
            
    def on_error(self, ws, error):
        print(f"[ERROR] {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        print(f"[CLOSED] Status: {close_status_code}, Message: {close_msg}")
        
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        print("[CONNECTED] WebSocket connected")
        
        # Phoenix channels join sequence
        # First join the Phoenix channel
        join_msg = json.dumps([
            "1",  # join_ref
            "1",  # ref
            "phoenix",  # topic
            "phx_join",  # event
            {}  # payload
        ])
        print(f"[SENDING] Join: {join_msg}")
        ws.send(join_msg)
        
        # Start heartbeat
        def heartbeat():
            ref = 1
            while self.running:
                ref += 1
                heartbeat_msg = json.dumps([
                    None,  # join_ref
                    str(ref),  # ref
                    "phoenix",  # topic
                    "heartbeat",  # event
                    {}  # payload
                ])
                print(f"[SENDING] Heartbeat: {heartbeat_msg}")
                ws.send(heartbeat_msg)
                time.sleep(30)  # Phoenix default heartbeat interval
                
        threading.Thread(target=heartbeat, daemon=True).start()
        
        # Try to join the LiveView channel
        time.sleep(1)
        if hasattr(self, 'phx_session'):
            # Attempt to join the LiveView session
            lv_join = json.dumps([
                "2",  # join_ref
                "2",  # ref
                f"lvu:{self.phx_session}",  # topic (LiveView session)
                "phx_join",  # event
                {
                    "url": self.base_url + "/",
                    "params": {
                        "_csrf_token": getattr(self, 'csrf_token', ''),
                        "_mounts": 0
                    },
                    "session": self.phx_session,
                    "static": ""
                }
            ])
            print(f"[SENDING] LiveView Join: {lv_join[:100]}...")
            ws.send(lv_join)
            
    def connect(self):
        """Connect to WebSocket"""
        # First get session
        self.get_session()
        
        # Setup WebSocket with cookies
        headers = {
            "Origin": self.base_url,
            "Cookie": "; ".join([f"{k}={v}" for k, v in self.session.cookies.items()])
        }
        
        print(f"\nConnecting to WebSocket: {self.ws_url}")
        print(f"Headers: {headers}")
        
        # Create WebSocket app
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run WebSocket
        try:
            self.ws.run_forever()
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Closing WebSocket...")
            self.running = False

if __name__ == "__main__":
    print("Solar Assistant WebSocket Monitor")
    print("=" * 50)
    
    monitor = SolarAssistantWebSocket()
    monitor.connect()