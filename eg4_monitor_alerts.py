#!/usr/bin/env python3
"""
EG4 18kPV Monitoring and Email Alert System
Monitors the inverter via IoTOS protocol and sends email alerts for specific events
"""

import socket
import struct
import time
import binascii
import json
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

class EG4Monitor:
    def __init__(self):
        # EG4 Configuration
        self.eg4_ip = os.getenv('EG4_IP', '172.16.107.53')
        self.eg4_port = 8000
        
        # Email Configuration (you'll need to set these in .env)
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.alert_email = os.getenv('ALERT_EMAIL', '')
        
        # Monitoring state
        self.socket = None
        self.monitoring = False
        self.last_reading = {}
        self.alerts_sent = {}
        
        # Alert conditions
        self.alert_conditions = {
            'connection_lost': {
                'description': 'Lost connection to inverter',
                'cooldown': 300  # 5 minutes
            },
            'power_outage': {
                'description': 'Grid power lost',
                'cooldown': 60
            },
            'battery_low': {
                'description': 'Battery level below threshold',
                'threshold': 20,  # percentage
                'cooldown': 600  # 10 minutes
            },
            'high_temperature': {
                'description': 'Temperature above threshold',
                'threshold': 50,  # Celsius
                'cooldown': 300
            },
            'inverter_fault': {
                'description': 'Inverter fault detected',
                'cooldown': 60
            },
            'daily_summary': {
                'description': 'Daily energy summary',
                'cooldown': 86400  # 24 hours
            }
        }
    
    def connect(self):
        """Connect to EG4 inverter"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.eg4_ip, self.eg4_port))
            print(f"✓ Connected to EG4 at {self.eg4_ip}:{self.eg4_port}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            self.check_alert('connection_lost', {'error': str(e)})
            return False
    
    def disconnect(self):
        """Disconnect from inverter"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def send_receive(self, command):
        """Send command and receive response"""
        if not self.socket:
            return None
            
        try:
            self.socket.send(command)
            self.socket.settimeout(5)
            response = self.socket.recv(4096)
            return response
        except:
            return None
    
    def parse_iotos_data(self, response):
        """Parse IoTOS response into meaningful data"""
        if not response or len(response) < 50:
            return None
            
        data = {
            'timestamp': datetime.now().isoformat(),
            'raw': binascii.hexlify(response).decode(),
            'serial': None,
            'device_id': None,
            'values': {}
        }
        
        # Extract serial number (we know it's at offset 8)
        try:
            serial_start = 8
            serial_end = response.find(b'\x00', serial_start)
            if serial_end > serial_start:
                data['serial'] = response[serial_start:serial_end].decode('ascii', errors='ignore')
        except:
            pass
        
        # Extract device ID
        try:
            # Device ID appears after serial
            id_match = response[20:35].decode('ascii', errors='ignore')
            if id_match:
                data['device_id'] = ''.join(c for c in id_match if c.isdigit())
        except:
            pass
        
        # Try to extract numeric values (this is speculative based on typical inverter data)
        # Real implementation would need proper protocol documentation
        try:
            # Look for patterns that might be readings
            # These offsets are guesses and would need to be verified
            if len(response) > 60:
                # Possible voltage/current/power values as 2-byte integers
                data['values']['voltage'] = struct.unpack('>H', response[40:42])[0] / 10.0  # V
                data['values']['current'] = struct.unpack('>H', response[42:44])[0] / 10.0  # A
                data['values']['power'] = struct.unpack('>H', response[44:46])[0]  # W
                data['values']['temperature'] = response[50] - 40  # Common temp encoding
                data['values']['status'] = response[35]
        except:
            pass
        
        return data
    
    def get_inverter_data(self):
        """Get current data from inverter"""
        # Use the command that worked in our tests
        command = b'\xa1\x1a\x05\x00'
        
        response = self.send_receive(command)
        if response:
            return self.parse_iotos_data(response)
        return None
    
    def check_alert(self, alert_type, data=None):
        """Check if an alert should be sent"""
        now = time.time()
        
        # Check cooldown
        if alert_type in self.alerts_sent:
            last_sent = self.alerts_sent[alert_type]
            cooldown = self.alert_conditions[alert_type].get('cooldown', 300)
            if now - last_sent < cooldown:
                return False
        
        # Send alert
        self.send_alert(alert_type, data)
        self.alerts_sent[alert_type] = now
        return True
    
    def send_alert(self, alert_type, data=None):
        """Send email alert"""
        if not self.smtp_username or not self.alert_email:
            print(f"⚠ Email not configured for alert: {alert_type}")
            return
        
        condition = self.alert_conditions[alert_type]
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = self.smtp_username
        msg['To'] = self.alert_email
        msg['Subject'] = f"EG4 Alert: {condition['description']}"
        
        # Email body
        body = f"""
EG4 18kPV Inverter Alert

Alert Type: {condition['description']}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Inverter IP: {self.eg4_ip}

Details:
"""
        
        if data:
            for key, value in data.items():
                body += f"  {key}: {value}\n"
        
        if self.last_reading:
            body += f"\nLast Reading:\n"
            body += f"  Serial: {self.last_reading.get('serial', 'Unknown')}\n"
            if 'values' in self.last_reading:
                for key, value in self.last_reading['values'].items():
                    body += f"  {key}: {value}\n"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print(f"✓ Alert sent: {alert_type}")
        except Exception as e:
            print(f"✗ Failed to send alert: {e}")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print("\nStarting EG4 monitoring...")
        
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        
        while self.monitoring:
            try:
                # Get data from inverter
                data = self.get_inverter_data()
                
                if data:
                    self.last_reading = data
                    reconnect_attempts = 0
                    
                    # Check for alert conditions
                    if 'values' in data:
                        values = data['values']
                        
                        # Check battery level
                        if 'battery_percent' in values:
                            if values['battery_percent'] < self.alert_conditions['battery_low']['threshold']:
                                self.check_alert('battery_low', {'level': values['battery_percent']})
                        
                        # Check temperature
                        if 'temperature' in values:
                            if values['temperature'] > self.alert_conditions['high_temperature']['threshold']:
                                self.check_alert('high_temperature', {'temperature': values['temperature']})
                        
                        # Check for faults
                        if 'status' in values and values['status'] != 0:
                            self.check_alert('inverter_fault', {'status_code': values['status']})
                    
                    # Log data
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Reading received")
                    if data.get('serial'):
                        print(f"  Serial: {data['serial']}")
                    if 'values' in data and data['values']:
                        for key, value in data['values'].items():
                            print(f"  {key}: {value}")
                
                else:
                    # No data received
                    reconnect_attempts += 1
                    if reconnect_attempts >= max_reconnect_attempts:
                        print("✗ Lost connection to inverter")
                        self.check_alert('connection_lost', {'attempts': reconnect_attempts})
                        
                        # Try to reconnect
                        self.disconnect()
                        time.sleep(10)
                        if self.connect():
                            reconnect_attempts = 0
                        else:
                            time.sleep(30)  # Wait longer before next attempt
                
                # Check for daily summary (at specific time)
                hour = datetime.now().hour
                if hour == 20 and 'daily_summary' not in self.alerts_sent:  # 8 PM
                    self.send_daily_summary()
                
            except Exception as e:
                print(f"✗ Monitor error: {e}")
                time.sleep(5)
            
            time.sleep(30)  # Poll every 30 seconds
    
    def send_daily_summary(self):
        """Send daily energy summary"""
        # This would aggregate data from the day
        # For now, just send current status
        self.check_alert('daily_summary', self.last_reading)
    
    def start_monitoring(self):
        """Start monitoring in background thread"""
        if not self.connect():
            return False
        
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        self.disconnect()

def main():
    """Main entry point"""
    monitor = EG4Monitor()
    
    print("EG4 18kPV Monitoring and Alert System")
    print("=" * 50)
    
    # Check email configuration
    if not monitor.smtp_username:
        print("\n⚠ Email not configured. Add to .env file:")
        print("  SMTP_SERVER=smtp.gmail.com")
        print("  SMTP_PORT=587")
        print("  SMTP_USERNAME=your-email@gmail.com")
        print("  SMTP_PASSWORD=your-app-password")
        print("  ALERT_EMAIL=recipient@example.com")
    
    # Start monitoring
    if monitor.start_monitoring():
        print("\n✓ Monitoring started. Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
            monitor.stop_monitoring()
            print("✓ Monitor stopped")
    else:
        print("\n✗ Failed to start monitoring")

if __name__ == "__main__":
    main()