#!/usr/bin/env python3
import websocket
import json
import requests
import time
import re

class SolarAssistantLiveCapture:
    def __init__(self):
        self.base_url = "http://172.16.106.13"
        self.ws_url = "ws://172.16.106.13/live/websocket?vsn=2.0.0"
        self.session = requests.Session()
        self.ws = None
        self.message_count = 0
        self.max_messages = 50
        
    def get_session(self):
        """Get a session cookie by loading the main page"""
        response = self.session.get(f"{self.base_url}/")
        print(f"Got session cookie: {self.session.cookies.get('_solar_assistant_key', 'None')[:50]}...")
        
        # Extract LiveView session data
        match = re.search(r'data-phx-session="([^"]+)"', response.text)
        if match:
            self.phx_session = match.group(1)
            print(f"PHX Session: {self.phx_session[:50]}...")
            
        # Extract CSRF token
        match = re.search(r'name="csrf-token" content="([^"]+)"', response.text)
        if match:
            self.csrf_token = match.group(1)
            
        # Extract phx ID
        match = re.search(r'id="(phx-[^"]+)"', response.text)
        if match:
            self.phx_id = match.group(1)
            print(f"PHX ID: {self.phx_id}")
            
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        self.message_count += 1
        
        try:
            data = json.loads(message)
            if isinstance(data, list) and len(data) >= 5:
                join_ref, ref, topic, event, payload = data[:5]
                
                # Only print interesting events
                if event in ["phx_reply", "diff"]:
                    print(f"\n[MSG {self.message_count}] Event: {event}, Topic: {topic}")
                    
                    # Look for data updates in the payload
                    if isinstance(payload, dict):
                        if "rendered" in payload:
                            # This might contain the actual HTML with data
                            print("Found rendered content")
                            # Extract numbers from the rendered HTML
                            rendered = str(payload["rendered"])
                            numbers = re.findall(r'(\d+\.?\d*)\s*(W|V|A|%|kW)', rendered)
                            if numbers:
                                print("Extracted values:")
                                for num, unit in numbers[:10]:
                                    print(f"  {num} {unit}")
                                    
                        elif "diff" in payload:
                            print(f"Diff update: {json.dumps(payload['diff'], indent=2)}")
                            
        except json.JSONDecodeError:
            pass
            
        if self.message_count >= self.max_messages:
            ws.close()
            
    def on_error(self, ws, error):
        print(f"[ERROR] {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        print(f"\n[CLOSED] Captured {self.message_count} messages")
        
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        print("[CONNECTED] WebSocket connected")
        
        # Join Phoenix channel
        join_msg = json.dumps([
            "1",  # join_ref
            "1",  # ref
            "phoenix",  # topic
            "phx_join",  # event
            {}  # payload
        ])
        ws.send(join_msg)
        
        # Join LiveView session
        time.sleep(0.5)
        lv_join = json.dumps([
            "2",  # join_ref
            "2",  # ref
            f"lv:{self.phx_id}",  # topic
            "phx_join",  # event
            {
                "redirect": "",
                "url": self.base_url + "/",
                "params": {
                    "_csrf_token": self.csrf_token,
                    "_mounts": 0
                },
                "session": self.phx_session,
                "static": self.phx_session
            }
        ])
        ws.send(lv_join)
        
        # Send a heartbeat after joining
        time.sleep(1)
        heartbeat = json.dumps([None, "3", "phoenix", "heartbeat", {}])
        ws.send(heartbeat)
        
    def capture(self):
        """Connect and capture WebSocket data"""
        # First get session
        self.get_session()
        
        # Setup WebSocket with cookies
        headers = {
            "Origin": self.base_url,
            "Cookie": "; ".join([f"{k}={v}" for k, v in self.session.cookies.items()])
        }
        
        print(f"\nConnecting to WebSocket...")
        
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
        self.ws.run_forever()

if __name__ == "__main__":
    print("Solar Assistant Live WebSocket Capture")
    print("=" * 50)
    
    capture = SolarAssistantLiveCapture()
    capture.capture()