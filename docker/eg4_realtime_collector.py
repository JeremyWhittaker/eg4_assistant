#!/usr/bin/env python3
"""
Real-time EG4 18kPV Data Collector
Based on Solar Assistant's implementation
"""

import os
import socket
import struct
import time
import json
import logging
from datetime import datetime
from influxdb import InfluxDBClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EG418kPVCollector:
    def __init__(self):
        # EG4 inverter settings
        self.inverter_ip = os.environ.get('INVERTER_IP', '172.16.107.129')
        self.inverter_port = 8000  # IoTOS protocol port
        
        # InfluxDB settings
        self.influx_host = os.environ.get('INFLUXDB_HOST', 'influxdb')
        self.influx_port = int(os.environ.get('INFLUXDB_PORT', '8086'))
        self.influx_db = os.environ.get('INFLUXDB_DB', 'solar_assistant')
        self.influx_user = os.environ.get('INFLUXDB_USER', 'solar')
        self.influx_password = os.environ.get('INFLUXDB_PASSWORD', 'solar123')
        
        # Poll interval
        self.poll_interval = int(os.environ.get('POLL_INTERVAL', '5'))
        
        # Initialize InfluxDB client
        self.influx_client = None
        self.connect_influxdb()
        
    def connect_influxdb(self):
        """Connect to InfluxDB"""
        try:
            self.influx_client = InfluxDBClient(
                host=self.influx_host,
                port=self.influx_port,
                username=self.influx_user,
                password=self.influx_password,
                database=self.influx_db
            )
            
            # Create database if it doesn't exist
            dbs = self.influx_client.get_list_database()
            if not any(db['name'] == self.influx_db for db in dbs):
                self.influx_client.create_database(self.influx_db)
                logger.info(f"Created database: {self.influx_db}")
            
            logger.info("Connected to InfluxDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            return False
    
    def parse_eg4_response(self, response):
        """Parse EG4 18kPV IoTOS protocol response"""
        if not response or len(response) < 100:
            return None
            
        # Verify header
        if response[0] != 0xa1:
            logger.warning("Invalid response header")
            return None
            
        try:
            # Extract device info
            device_id = response[8:18].decode('ascii', errors='ignore').rstrip('\x00')
            
            # Parse 16-bit values from the data section
            # Based on the response pattern, real data starts around position 36
            data = {}
            
            # Extract values as 16-bit unsigned integers
            # Position 36-37: PV1 voltage (0.1V resolution)
            data['pv1_voltage'] = struct.unpack('>H', response[36:38])[0] / 10.0
            
            # Position 38-39: PV1 current (0.1A resolution)
            data['pv1_current'] = struct.unpack('>H', response[38:40])[0] / 10.0
            
            # Position 40-41: PV2 voltage
            data['pv2_voltage'] = struct.unpack('>H', response[40:42])[0] / 10.0
            
            # Position 42-43: PV2 current
            data['pv2_current'] = struct.unpack('>H', response[42:44])[0] / 10.0
            
            # Calculate PV power
            data['pv1_power'] = int(data['pv1_voltage'] * data['pv1_current'])
            data['pv2_power'] = int(data['pv2_voltage'] * data['pv2_current'])
            
            # Battery data (positions vary, need to analyze more)
            # Position 78-79 seems to have battery related data
            data['battery_voltage'] = struct.unpack('>H', response[78:80])[0] / 10.0
            data['battery_current'] = struct.unpack('>h', response[80:82])[0] / 10.0  # Signed
            data['battery_power'] = int(data['battery_voltage'] * data['battery_current'])
            
            # Battery SOC might be at position 86
            if response[86] <= 100:
                data['battery_soc'] = response[86]
            else:
                data['battery_soc'] = 0
            
            # Grid/Load data needs more analysis
            # For now, estimate based on power flow
            data['total_pv_power'] = data['pv1_power'] + data['pv2_power']
            data['load_power'] = 1500  # Placeholder
            data['grid_power'] = data['load_power'] - data['total_pv_power'] - data['battery_power']
            
            # Add device info
            data['device_id'] = device_id
            data['timestamp'] = datetime.utcnow().isoformat()
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    def collect_data(self):
        """Collect data from EG4 inverter"""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            # Connect to inverter
            sock.connect((self.inverter_ip, self.inverter_port))
            logger.info(f"Connected to EG4 at {self.inverter_ip}:{self.inverter_port}")
            
            # Send query command
            query_command = b'\xa1\x1a\x05\x00'
            sock.send(query_command)
            
            # Receive response
            sock.settimeout(5)
            response = sock.recv(4096)
            sock.close()
            
            if response:
                logger.info(f"Received {len(response)} bytes from inverter")
                data = self.parse_eg4_response(response)
                
                if data:
                    logger.info(f"Parsed data: PV={data['total_pv_power']}W, Battery={data['battery_power']}W, SOC={data['battery_soc']}%")
                    return data
                else:
                    logger.warning("Failed to parse response")
            else:
                logger.warning("No response from inverter")
                
        except socket.timeout:
            logger.warning("Connection timeout")
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
        
        return None
    
    def write_to_influxdb(self, data):
        """Write data to InfluxDB"""
        try:
            # Remove non-numeric fields for InfluxDB
            fields = {k: v for k, v in data.items() if k not in ['device_id', 'timestamp']}
            
            json_body = [
                {
                    "measurement": "inverter_data",
                    "tags": {
                        "inverter": "eg4_18kpv",
                        "device_id": data.get('device_id', 'unknown'),
                        "location": "main"
                    },
                    "time": data['timestamp'],
                    "fields": fields
                }
            ]
            
            self.influx_client.write_points(json_body)
            logger.info("Data written to InfluxDB")
            
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting EG4 18kPV Real-time Data Collector...")
        logger.info(f"Inverter: {self.inverter_ip}:{self.inverter_port}")
        logger.info(f"InfluxDB: {self.influx_host}:{self.influx_port}/{self.influx_db}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        while True:
            try:
                # Collect data
                data = self.collect_data()
                
                if data:
                    # Write to InfluxDB
                    self.write_to_influxdb(data)
                    
                    # Also save to file for debugging
                    with open('/tmp/eg4_latest.json', 'w') as f:
                        json.dump(data, f, indent=2)
                
                # Wait for next poll
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Stopping collector...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(self.poll_interval)

if __name__ == "__main__":
    collector = EG418kPVCollector()
    collector.run()