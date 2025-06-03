#!/usr/bin/env python3
"""
Test connection to EG4 18kPV inverter
Based on the information:
- Local IP: 172.16.107.53
- Web interface: http://172.16.107.53/index_en.html
- IoTOS dongle using TCP port 8000 for local connection
- Cloud server: 3.101.7.137 port 4346
"""

import socket
import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
EG4_IP = os.getenv('EG4_IP', '172.16.107.53')
EG4_USERNAME = os.getenv('EG4_USERNAME', 'admin')
EG4_PASSWORD = os.getenv('EG4_PASSWORD', 'admin')

def test_tcp_connection(host, port, timeout=5):
    """Test TCP connection to a host:port"""
    print(f"\nTesting TCP connection to {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ Successfully connected to {host}:{port}")
            return True
        else:
            print(f"✗ Failed to connect to {host}:{port} (Error code: {result})")
            return False
    except Exception as e:
        print(f"✗ Exception connecting to {host}:{port}: {e}")
        return False

def test_web_interface():
    """Test web interface access"""
    print(f"\nTesting web interface at http://{EG4_IP}/index_en.html...")
    try:
        # Test without auth first
        response = requests.get(f"http://{EG4_IP}/index_en.html", timeout=5)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 401:
            print("Authentication required. Trying with credentials...")
            response = requests.get(
                f"http://{EG4_IP}/index_en.html", 
                auth=(EG4_USERNAME, EG4_PASSWORD),
                timeout=5
            )
            print(f"Authenticated response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Web interface accessible")
            # Look for API endpoints in the HTML
            if 'api' in response.text.lower() or 'json' in response.text.lower():
                print("Found potential API references in web interface")
            return True
    except Exception as e:
        print(f"✗ Error accessing web interface: {e}")
        return False

def probe_modbus_tcp():
    """Test for Modbus TCP on standard port 502"""
    return test_tcp_connection(EG4_IP, 502)

def probe_iotos_port():
    """Test IoTOS dongle port 8000"""
    return test_tcp_connection(EG4_IP, 8000)

def send_iotos_probe(host, port):
    """Send a probe to IoTOS port to see what protocol it uses"""
    print(f"\nProbing IoTOS protocol on {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        # Try sending a simple query
        # Common protocols: JSON-RPC, proprietary binary, or text-based
        test_messages = [
            b'{"method":"get_status","id":1}\n',  # JSON-RPC style
            b'GET /status HTTP/1.0\r\n\r\n',      # HTTP style
            b'STATUS\n',                          # Simple text
            b'\x01\x03\x00\x00\x00\x01\x84\x0a', # Modbus RTU over TCP (read holding registers)
        ]
        
        for msg in test_messages:
            print(f"Sending: {msg[:50]}...")
            sock.send(msg)
            sock.settimeout(2)
            
            try:
                response = sock.recv(1024)
                if response:
                    print(f"Received response: {response[:100]}")
                    # Try to decode as text
                    try:
                        print(f"Decoded: {response.decode('utf-8', errors='ignore')[:100]}")
                    except:
                        pass
                    break
            except socket.timeout:
                continue
        
        sock.close()
    except Exception as e:
        print(f"Error probing IoTOS: {e}")

def scan_common_ports():
    """Scan common inverter/IoT ports"""
    common_ports = [
        (80, "HTTP"),
        (443, "HTTPS"),
        (502, "Modbus TCP"),
        (1502, "Alt Modbus"),
        (8000, "IoTOS"),
        (8080, "HTTP Alt"),
        (9999, "Common IoT"),
        (23, "Telnet"),
        (22, "SSH"),
    ]
    
    print("\nScanning common ports...")
    open_ports = []
    for port, name in common_ports:
        if test_tcp_connection(EG4_IP, port, timeout=1):
            open_ports.append((port, name))
    
    return open_ports

if __name__ == "__main__":
    print(f"Testing EG4 18kPV connection at {EG4_IP}")
    print("=" * 50)
    
    # Test web interface
    test_web_interface()
    
    # Scan ports
    open_ports = scan_common_ports()
    
    if open_ports:
        print(f"\nOpen ports found: {open_ports}")
        
        # If port 8000 is open, probe it
        if any(p[0] == 8000 for p in open_ports):
            send_iotos_probe(EG4_IP, 8000)
    
    print("\nConnection test complete.")