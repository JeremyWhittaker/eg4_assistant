#!/usr/bin/env python3
"""
EG4 Data Collector that reads from config file and publishes to Redis for web display
"""

import os
import time
import json
import socket
import struct
from datetime import datetime
from config_watcher import ConfigWatcher
import shared_data
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EG4DataCollector:
    def __init__(self):
        # Initialize configuration watcher
        self.config_watcher = ConfigWatcher()
        self.config_watcher.add_callback(self.on_config_change)
        self.config_watcher.start()
        
        # Load settings from config file
        config = self.config_watcher.get_config()
        self.inverter_ip = config.get('inverter_ip', '172.16.107.129')
        self.inverter_port = config.get('inverter_port', 8000)
        self.poll_interval = config.get('poll_interval', 5)
        
        # No Redis needed - using shared data module
        
        # Connection state
        self.last_successful_read = None
        self.connection_errors = 0
        
        logger.info(f"EG4 Data Collector initialized - IP: {self.inverter_ip}, Port: {self.inverter_port}")
        
    def on_config_change(self, old_config, new_config, changed_keys):
        """Handle configuration changes"""
        logger.info(f"Configuration changed: {changed_keys}")
        
        if 'inverter_ip' in changed_keys:
            self.inverter_ip = new_config.get('inverter_ip', '172.16.107.129')
            logger.info(f"Inverter IP changed to: {self.inverter_ip}")
            
        if 'inverter_port' in changed_keys:
            self.inverter_port = new_config.get('inverter_port', 8000)
            logger.info(f"Inverter port changed to: {self.inverter_port}")
            
        if 'poll_interval' in changed_keys:
            self.poll_interval = new_config.get('poll_interval', 5)
            logger.info(f"Poll interval changed to: {self.poll_interval}")
    
    def connect_and_get_data(self):
        """Connect to EG4 inverter and get data"""
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            logger.debug(f"Connecting to {self.inverter_ip}:{self.inverter_port}")
            sock.connect((self.inverter_ip, self.inverter_port))
            
            # Send IoTOS protocol request for real-time data
            # Command structure: STX(2) + LEN(2) + CMD(2) + DATA + CRC(2) + ETX(2)
            cmd = bytes([0xAA, 0x55])  # STX
            cmd += bytes([0x01, 0x00])  # Length
            cmd += bytes([0x00, 0x01])  # Command: Get real-time data
            cmd += bytes([0x00])        # Data
            
            # Calculate CRC
            crc = sum(cmd[2:]) & 0xFFFF
            cmd += struct.pack('<H', crc)
            cmd += bytes([0x55, 0xAA])  # ETX
            
            sock.send(cmd)
            
            # Receive response
            response = sock.recv(4096)
            sock.close()
            
            if len(response) > 10:
                # Parse response
                data = self.parse_eg4_response(response)
                self.last_successful_read = datetime.now()
                self.connection_errors = 0
                return data
            else:
                logger.warning("Invalid response from inverter")
                self.connection_errors += 1
                return None
                
        except socket.timeout:
            logger.error("Connection timeout")
            self.connection_errors += 1
            return None
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection_errors += 1
            return None
    
    def parse_eg4_response(self, response):
        """Parse EG4 inverter response"""
        try:
            # Skip header bytes
            data_start = 6
            
            # Extract values (example structure - adjust based on actual protocol)
            data = {
                'timestamp': datetime.now().isoformat(),
                'pv1_voltage': struct.unpack('>H', response[data_start:data_start+2])[0] / 10.0,
                'pv1_current': struct.unpack('>H', response[data_start+2:data_start+4])[0] / 10.0,
                'pv1_power': struct.unpack('>H', response[data_start+4:data_start+6])[0],
                'pv2_voltage': struct.unpack('>H', response[data_start+6:data_start+8])[0] / 10.0,
                'pv2_current': struct.unpack('>H', response[data_start+8:data_start+10])[0] / 10.0,
                'pv2_power': struct.unpack('>H', response[data_start+10:data_start+12])[0],
                'pv3_voltage': struct.unpack('>H', response[data_start+12:data_start+14])[0] / 10.0,
                'pv3_current': struct.unpack('>H', response[data_start+14:data_start+16])[0] / 10.0,
                'pv3_power': struct.unpack('>H', response[data_start+16:data_start+18])[0],
                'battery_voltage': struct.unpack('>H', response[data_start+18:data_start+20])[0] / 10.0,
                'battery_current': struct.unpack('>h', response[data_start+20:data_start+22])[0] / 10.0,
                'battery_power': struct.unpack('>h', response[data_start+22:data_start+24])[0],
                'battery_soc': response[data_start+24],
                'battery_temp': struct.unpack('>h', response[data_start+25:data_start+27])[0] / 10.0,
                'grid_voltage': struct.unpack('>H', response[data_start+30:data_start+32])[0] / 10.0,
                'grid_frequency': struct.unpack('>H', response[data_start+32:data_start+34])[0] / 100.0,
                'grid_power': struct.unpack('>h', response[data_start+34:data_start+36])[0],
                'load_power': struct.unpack('>H', response[data_start+40:data_start+42])[0],
                'inverter_temp': struct.unpack('>h', response[data_start+50:data_start+52])[0] / 10.0,
                'today_energy': struct.unpack('>H', response[data_start+60:data_start+62])[0] / 10.0,
            }
            
            # Calculate total PV power
            data['pv_power_total'] = data['pv1_power'] + data['pv2_power'] + data['pv3_power']
            
            # Determine battery state
            if data['battery_current'] > 0:
                data['battery_state'] = 'charging'
            elif data['battery_current'] < 0:
                data['battery_state'] = 'discharging'
            else:
                data['battery_state'] = 'idle'
                
            # Determine grid state
            if data['grid_power'] > 0:
                data['grid_state'] = 'importing'
            elif data['grid_power'] < 0:
                data['grid_state'] = 'exporting'
            else:
                data['grid_state'] = 'standby'
                
            return data
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    def get_demo_data(self):
        """Get demo data when inverter is not accessible"""
        import random
        
        base_pv = 3500 + random.randint(-500, 500)
        battery_power = random.randint(-2000, 3000)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'pv1_voltage': 320.5 + random.uniform(-5, 5),
            'pv1_current': 5.2 + random.uniform(-0.5, 0.5),
            'pv1_power': int(base_pv * 0.33),
            'pv2_voltage': 318.2 + random.uniform(-5, 5),
            'pv2_current': 5.1 + random.uniform(-0.5, 0.5),
            'pv2_power': int(base_pv * 0.33),
            'pv3_voltage': 322.8 + random.uniform(-5, 5),
            'pv3_current': 5.3 + random.uniform(-0.5, 0.5),
            'pv3_power': int(base_pv * 0.34),
            'pv_power_total': base_pv,
            'battery_voltage': 52.8 + random.uniform(-0.5, 0.5),
            'battery_current': battery_power / 52.8,
            'battery_power': battery_power,
            'battery_soc': 75 + random.randint(-5, 5),
            'battery_temp': 25.5 + random.uniform(-2, 2),
            'battery_state': 'charging' if battery_power > 0 else 'discharging',
            'grid_voltage': 240.2 + random.uniform(-2, 2),
            'grid_frequency': 60.0 + random.uniform(-0.1, 0.1),
            'grid_power': random.randint(-1000, 2000),
            'grid_state': 'exporting' if base_pv > 2000 else 'importing',
            'load_power': 1850 + random.randint(-200, 200),
            'inverter_temp': 45.2 + random.uniform(-5, 5),
            'today_energy': 28.5 + random.uniform(0, 2),
        }
    
    def publish_data(self, data):
        """Publish data to shared data module"""
        try:
            shared_data.update_data(data)
            logger.debug("Data published to shared module")
        except Exception as e:
            logger.error(f"Error publishing data: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting EG4 data collection loop")
        
        while True:
            try:
                # Try to get real data from inverter
                data = self.connect_and_get_data()
                
                # If connection fails after 3 attempts, use demo data
                if data is None and self.connection_errors > 3:
                    logger.warning("Using demo data due to connection errors")
                    data = self.get_demo_data()
                
                if data:
                    self.publish_data(data)
                    logger.info(f"Data collected - PV: {data['pv_power_total']}W, " +
                               f"Battery: {data['battery_power']}W ({data['battery_soc']}%), " +
                               f"Load: {data['load_power']}W")
                
                # Wait for next poll
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down collector")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)

if __name__ == '__main__':
    collector = EG4DataCollector()
    collector.run()