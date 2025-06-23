#!/usr/bin/env python3
"""Test MQTT connection to Solar Assistant"""

import paho.mqtt.client as mqtt
import json
import time

def on_connect(client, userdata, flags, rc):
    print(f'Connected with result code {rc}')
    # Subscribe to all Solar Assistant topics
    client.subscribe('solar-assistant/#')
    client.subscribe('eg4assistant/#')
    client.subscribe('solar_assistant/#')

def on_message(client, userdata, msg):
    print(f'\nTopic: {msg.topic}')
    try:
        data = json.loads(msg.payload.decode())
        print(f'Data: {json.dumps(data, indent=2)}')
    except:
        print(f'Raw: {msg.payload.decode()}')

# Create MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    print("Connecting to Solar Assistant MQTT broker at 172.16.106.13:1883...")
    client.connect('172.16.106.13', 1883, 60)
    
    # Start loop
    client.loop_start()
    
    # Wait for messages
    print("Listening for MQTT messages for 20 seconds...")
    time.sleep(20)
    
    # Stop
    client.loop_stop()
    client.disconnect()
    
except Exception as e:
    print(f'Error: {e}')