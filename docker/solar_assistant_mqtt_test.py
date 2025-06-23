#!/usr/bin/env python3
"""
Test script to connect to Solar Assistant MQTT broker and discover topic structure
Requires: pip install paho-mqtt
"""

import socket
import time
import json

def test_mqtt_connection():
    """Test basic TCP connection to MQTT broker"""
    host = "172.16.109.214"
    port = 1883
    
    print(f"Testing MQTT connection to {host}:{port}...")
    
    try:
        # Test TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ MQTT port {port} is open on {host}")
            return True
        else:
            print(f"✗ MQTT port {port} is closed on {host}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing connection: {e}")
        return False

def discover_mqtt_topics():
    """
    Common Solar Assistant MQTT topic patterns to try:
    """
    common_topics = [
        "solar_assistant/#",
        "solarassistant/#", 
        "sa/#",
        "inverter/#",
        "battery/#",
        "grid/#",
        "load/#",
        "solar/#",
        "energy/#",
        "stat/#",
        "tele/#",
        "cmnd/#",
        "#"  # All topics
    ]
    
    print("\nCommon MQTT topics to try:")
    for topic in common_topics:
        print(f"  - {topic}")
    
    print("\nTo test with mosquitto client:")
    print("  mosquitto_sub -h 172.16.109.214 -p 1883 -t '#' -v")
    print("\nOr with authentication if required:")
    print("  mosquitto_sub -h 172.16.109.214 -p 1883 -u USERNAME -P PASSWORD -t '#' -v")

def main():
    print("Solar Assistant MQTT Discovery\n" + "="*40)
    
    # Test MQTT connection
    if test_mqtt_connection():
        print("\nMQTT broker is accessible!")
        discover_mqtt_topics()
        
        print("\n\nNext steps:")
        print("1. Configure MQTT in Solar Assistant web interface at:")
        print("   http://172.16.109.214/configuration/mqtt")
        print("2. Enable MQTT publishing if not already enabled")
        print("3. Use MQTT client to subscribe and discover exact topic structure")
        print("4. Document the topic/payload format for integration")
    else:
        print("\nMQTT broker is not accessible. Check Solar Assistant configuration.")

if __name__ == "__main__":
    main()