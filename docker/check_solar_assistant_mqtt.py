#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if rc == 0:
        print("Subscribing to all topics...")
        client.subscribe("#")
    else:
        print(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode('utf-8', errors='ignore')}")

# MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    print("Connecting to Solar Assistant MQTT at 172.16.109.214:1883...")
    client.connect("172.16.109.214", 1883, 60)
    
    # Run for 10 seconds
    start_time = time.time()
    while time.time() - start_time < 10:
        client.loop()
        
except Exception as e:
    print(f"Error: {e}")
finally:
    client.disconnect()