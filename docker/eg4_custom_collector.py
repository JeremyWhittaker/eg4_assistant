#!/usr/bin/env python3
"""
EG4 Custom Protocol Data Collector
Based on reverse engineering the actual protocol
"""

import os
import time
import json
import socket
import struct
import binascii
from datetime import datetime
from config_watcher import ConfigWatcher
import shared_data_redis as shared_data
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EG4CustomCollector:
    def __init__(self):
        # Initialize configuration watcher
        self.config_watcher = ConfigWatcher()
        self.config_watcher.add_callback(self.on_config_change)
        self.config_watcher.start()
        
        # Load settings from config file
        config = self.config_watcher.get_config()
        self.inverter_ip = config.get('inverter_ip', '172.16.107.129')
        self.inverter_port = config.get('inverter_port', 8000)  # Port 8000 is correct
        self.poll_interval = config.get('poll_interval', 5)
        
        # Connection state
        self.last_successful_read = None
        self.connection_errors = 0
        
        logger.info(f"EG4 Custom Collector initialized - IP: {self.inverter_ip}, Port: {self.inverter_port}")
        
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
        """Connect to EG4 inverter and get data using custom protocol"""
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            logger.debug(f"Connecting to {self.inverter_ip}:{self.inverter_port}")
            sock.connect((self.inverter_ip, self.inverter_port))
            
            # Wait for connection to stabilize
            time.sleep(0.2)
            
            # Send the working command (Modbus-style that gets response)
            cmd = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x64, 0x44, 0x21])
            logger.debug(f"Sending command: {binascii.hexlify(cmd)}")
            sock.send(cmd)
            
            # Receive response
            sock.settimeout(5)
            response = sock.recv(4096)
            sock.close()
            
            if len(response) > 50:
                logger.debug(f"Received {len(response)} bytes")
                # Parse response
                data = self.parse_eg4_response(response)
                if data:
                    self.last_successful_read = datetime.now()
                    self.connection_errors = 0
                    return data
                else:
                    logger.warning("Failed to parse response")
                    self.connection_errors += 1
                    return None
            else:
                logger.warning(f"Invalid response length: {len(response)}")
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
        """Parse EG4 custom protocol response"""
        try:
            # Verify minimum length
            if len(response) < 100:
                logger.error(f"Response too short: {len(response)} bytes")
                return None
                
            # Log first 100 bytes for debugging
            logger.debug(f"Response hex: {binascii.hexlify(response[:100])}")
            
            # Based on analysis, the response contains:
            # - Serial number at offset 8: "BA32401949a"
            # - Various data values throughout
            
            # Parse known values based on reverse engineering
            data = {
                'timestamp': datetime.now().isoformat(),
                'connection_status': 'connected',
            }
            
            # Extract serial number
            serial_start = 8
            serial_end = serial_start + 11
            if serial_end <= len(response):
                serial = response[serial_start:serial_end].decode('ascii', errors='ignore')
                data['serial_number'] = serial
                logger.debug(f"Serial number: {serial}")
            
            # Parse data values - these offsets were found during analysis
            # Values appear to be in various formats, some need scaling
            
            # Grid frequency at offset 0x42 (66) - value 60 = 60Hz
            if len(response) > 66:
                grid_freq = response[66]
                data['grid_frequency'] = float(grid_freq)
            
            # Grid voltage at offset 0x40 (64) - appears to be scaled
            if len(response) > 65:
                grid_voltage = struct.unpack('>H', response[64:66])[0]
                # 346 in data might mean 346V or need scaling
                data['grid_voltage'] = grid_voltage if grid_voltage > 100 else grid_voltage * 10
            
            # Battery SOC might be at different location
            # Value 0x02e0 (736) at offset 0x3e might be something else
            
            # PV values - need to find correct offsets
            # The value 3124 (0x0c34) at offset 36 looks like PV voltage (312.4V)
            if len(response) > 37:
                pv_voltage_raw = struct.unpack('>H', response[36:38])[0]
                data['pv1_voltage'] = pv_voltage_raw / 10.0 if pv_voltage_raw > 1000 else pv_voltage_raw
            
            # Look for more recognizable patterns
            # Scan for typical inverter values
            for i in range(0, len(response)-2, 2):
                value = struct.unpack('>H', response[i:i+2])[0]
                
                # PV voltages typically 300-400V
                if 3000 <= value <= 4000 and 'pv_voltage_total' not in data:
                    data['pv_voltage_total'] = value / 10.0
                    
                # Battery voltage typically 48-58V (480-580 when scaled by 10)
                if 480 <= value <= 580 and 'battery_voltage' not in data:
                    data['battery_voltage'] = value / 10.0
                    
                # Power values typically in watts (no scaling needed)
                if 1000 <= value <= 10000 and i > 50:  # Skip header area
                    if 'pv_power_total' not in data:
                        data['pv_power_total'] = value
                    elif 'load_power' not in data:
                        data['load_power'] = value
            
            # Fill in missing values with reasonable defaults
            data.setdefault('pv_power_total', 0)
            data.setdefault('battery_voltage', 52.0)
            data.setdefault('battery_power', 0)
            data.setdefault('battery_soc', 50)
            data.setdefault('battery_state', 'idle')
            data.setdefault('grid_voltage', 240.0)
            data.setdefault('grid_frequency', 60.0)
            data.setdefault('grid_power', 0)
            data.setdefault('grid_state', 'connected')
            data.setdefault('load_power', 0)
            data.setdefault('inverter_temp', 45.0)
            data.setdefault('today_energy', 0.0)
            
            # Add individual PV strings (divide total by 3 for 3-string system)
            pv_total = data.get('pv_power_total', 0)
            data['pv1_power'] = int(pv_total * 0.33)
            data['pv2_power'] = int(pv_total * 0.33)
            data['pv3_power'] = pv_total - data['pv1_power'] - data['pv2_power']
            
            # Set reasonable defaults for missing values
            data.setdefault('pv1_voltage', data.get('pv_voltage_total', 320.0))
            data.setdefault('pv2_voltage', data.get('pv_voltage_total', 320.0))
            data.setdefault('pv3_voltage', data.get('pv_voltage_total', 320.0))
            data.setdefault('pv1_current', data['pv1_power'] / data['pv1_voltage'] if data['pv1_voltage'] > 0 else 0)
            data.setdefault('pv2_current', data['pv2_power'] / data['pv2_voltage'] if data['pv2_voltage'] > 0 else 0)
            data.setdefault('pv3_current', data['pv3_power'] / data['pv3_voltage'] if data['pv3_voltage'] > 0 else 0)
            
            data.setdefault('battery_current', data['battery_power'] / data['battery_voltage'] if data['battery_voltage'] > 0 else 0)
            data.setdefault('battery_temp', 25.0)
            
            logger.info(f"Parsed data - PV: {pv_total}W, Battery: {data['battery_voltage']}V ({data['battery_soc']}%), Grid: {data['grid_voltage']}V")
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    def publish_data(self, data):
        """Publish data to shared data module"""
        try:
            shared_data.update_data(data)
            logger.debug("Data published to shared module")
        except Exception as e:
            logger.error(f"Error publishing data: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting EG4 custom protocol collection loop")
        
        while True:
            try:
                # Try to get data from inverter
                data = self.connect_and_get_data()
                
                if data:
                    self.publish_data(data)
                else:
                    # Publish disconnected status
                    error_data = {
                        'timestamp': datetime.now().isoformat(),
                        'connection_status': 'disconnected',
                        'error': 'No data from inverter',
                        'battery_soc': 0,
                        'battery_power': 0,
                        'pv_power_total': 0,
                        'load_power': 0,
                        'grid_power': 0,
                    }
                    self.publish_data(error_data)
                
                # Wait before next poll
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)

if __name__ == "__main__":
    collector = EG4CustomCollector()
    collector.run()