#!/usr/bin/env python3
"""
MQTT Bridge for Solar Assistant
Handles MQTT subscriptions and command processing
"""

import os
import json
import yaml
import logging
import paho.mqtt.client as mqtt
from datetime import datetime
import threading
import time

# Load configuration
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config/config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Setup logging
logger = logging.getLogger(__name__)

class MQTTBridge:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.running = True
        
    def on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to command topics
            prefix = config['mqtt']['topics']['prefix']
            client.subscribe(f"{prefix}/command/+")
            client.subscribe(f"{prefix}/set/+")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.info(f"Received message on {topic}: {payload}")
            
            # Process commands
            if "/command/" in topic:
                command = topic.split("/")[-1]
                self.process_command(command, payload)
            elif "/set/" in topic:
                setting = topic.split("/")[-1]
                self.process_setting(setting, payload)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        """Handle disconnection"""
        logger.warning(f"Disconnected from MQTT broker: {rc}")
        if rc != 0 and self.running:
            # Attempt to reconnect
            threading.Thread(target=self.reconnect, daemon=True).start()
    
    def reconnect(self):
        """Attempt to reconnect to MQTT broker"""
        while self.running:
            try:
                logger.info("Attempting to reconnect to MQTT broker...")
                self.client.connect(
                    config['mqtt']['host'],
                    config['mqtt']['port'],
                    60
                )
                break
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                time.sleep(30)
    
    def process_command(self, command, payload):
        """Process incoming commands"""
        logger.info(f"Processing command: {command}")
        
        if command == "restart":
            # Restart specific service
            service = payload.get('service')
            logger.info(f"Restarting service: {service}")
            
        elif command == "export":
            # Export data
            format = payload.get('format', 'csv')
            period = payload.get('period', 'day')
            logger.info(f"Exporting data: {format}, {period}")
            
        elif command == "backup":
            # Trigger backup
            logger.info("Triggering backup...")
    
    def process_setting(self, setting, payload):
        """Process setting changes"""
        logger.info(f"Processing setting: {setting}")
        
        # Update configuration
        # This would integrate with the main server
    
    def start(self):
        """Start the MQTT bridge"""
        try:
            if config['mqtt']['username']:
                self.client.username_pw_set(
                    config['mqtt']['username'],
                    config['mqtt']['password']
                )
            
            self.client.connect(
                config['mqtt']['host'],
                config['mqtt']['port'],
                60
            )
            
            self.client.loop_forever()
            
        except Exception as e:
            logger.error(f"Failed to start MQTT bridge: {e}")
    
    def stop(self):
        """Stop the MQTT bridge"""
        self.running = False
        self.client.disconnect()

if __name__ == '__main__':
    bridge = MQTTBridge()
    try:
        bridge.start()
    except KeyboardInterrupt:
        bridge.stop()