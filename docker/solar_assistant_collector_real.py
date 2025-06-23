#!/usr/bin/env python3
"""
Solar Assistant Compatible Data Collector - Real EG4 Version
Collects real data from EG4 18kPV and publishes in Solar Assistant format
"""

import os
import time
import json
import logging
import socket
import struct
from datetime import datetime
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SolarAssistantCollector:
    def __init__(self):
        # Settings
        self.inverter_ip = os.environ.get('INVERTER_IP', '172.16.107.129')
        self.inverter_port = 8000  # IoTOS port
        self.poll_interval = int(os.environ.get('POLL_INTERVAL', '5'))
        
        # MQTT settings
        self.mqtt_host = os.environ.get('MQTT_HOST', 'mqtt')
        self.mqtt_port = int(os.environ.get('MQTT_PORT', '1883'))
        self.mqtt_prefix = os.environ.get('MQTT_PREFIX', 'solar_assistant')
        
        # InfluxDB settings
        self.influx_host = os.environ.get('INFLUXDB_HOST', 'influxdb')
        self.influx_port = int(os.environ.get('INFLUXDB_PORT', '8086'))
        self.influx_db = os.environ.get('INFLUXDB_DB', 'solar_assistant')
        
        # Initialize clients
        self.mqtt_client = None
        self.influx_client = None
        
        self.connect_mqtt()
        self.connect_influxdb()
        
        # Daily totals
        self.daily_pv_energy = 0.0
        self.daily_grid_export = 0.0
        self.daily_grid_import = 0.0
        self.last_pv_power = 0
        
    def on_config_change(self, old_config, new_config, changed_keys):
        """Handle configuration changes"""
        logger.info(f"Configuration changed: {changed_keys}")
        
        # Check if critical settings changed
        reconnect_needed = False
        
        if 'inverter_ip' in changed_keys:
            self.inverter_ip = new_config.get('inverter_ip', '172.16.107.129')
            logger.info(f"Inverter IP changed to: {self.inverter_ip}")
            reconnect_needed = True
            
        if 'inverter_port' in changed_keys:
            self.inverter_port = new_config.get('inverter_port', 8000)
            logger.info(f"Inverter port changed to: {self.inverter_port}")
            reconnect_needed = True
            
        if 'poll_interval' in changed_keys:
            self.poll_interval = new_config.get('poll_interval', 5)
            logger.info(f"Poll interval changed to: {self.poll_interval}")
            
        # Reconnect if needed
        if reconnect_needed:
            logger.info("Reconnecting due to configuration change...")
            # Next poll will automatically use new settings
        
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            
    def connect_influxdb(self):
        """Connect to InfluxDB"""
        try:
            self.influx_client = InfluxDBClient(
                host=self.influx_host,
                port=self.influx_port,
                database=self.influx_db
            )
            
            # Create database if it doesn't exist
            dbs = self.influx_client.get_list_database()
            if not any(db['name'] == self.influx_db for db in dbs):
                self.influx_client.create_database(self.influx_db)
                logger.info(f"Created database: {self.influx_db}")
                
            logger.info("Connected to InfluxDB")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
    
    def parse_eg4_response(self, response):
        """Parse EG4 18kPV IoTOS protocol response"""
        if not response or len(response) < 117:
            return None
            
        try:
            # Based on our analysis of the EG4 responses
            data = {}
            
            # Extract serial numbers
            if len(response) >= 30:
                data['inverter_serial'] = response[8:19].decode('ascii', errors='ignore').rstrip('\x00')
                data['battery_serial'] = response[24:34].decode('ascii', errors='ignore').rstrip('\x00')
            
            # The data pattern shows values starting around position 36
            # These positions were determined by analyzing multiple responses
            
            # PV Data (positions may vary, these are estimates)
            if len(response) >= 90:
                # PV1 voltage and current
                data['pv1_voltage'] = struct.unpack('>H', response[60:62])[0] / 10.0
                data['pv1_current'] = struct.unpack('>H', response[62:64])[0] / 10.0
                data['pv1_power'] = int(data['pv1_voltage'] * data['pv1_current'])
                
                # PV2 voltage and current
                data['pv2_voltage'] = struct.unpack('>H', response[64:66])[0] / 10.0
                data['pv2_current'] = struct.unpack('>H', response[66:68])[0] / 10.0
                data['pv2_power'] = int(data['pv2_voltage'] * data['pv2_current'])
                
                # Battery data
                data['battery_voltage'] = struct.unpack('>H', response[70:72])[0] / 10.0
                data['battery_current'] = struct.unpack('>h', response[72:74])[0] / 10.0  # signed
                data['battery_power'] = int(data['battery_voltage'] * data['battery_current'])
                
                # Battery SOC might be a single byte
                if response[86] <= 100:
                    data['battery_soc'] = response[86]
                else:
                    data['battery_soc'] = 50  # default
                
                # Grid/AC data (estimated positions)
                data['grid_voltage'] = struct.unpack('>H', response[80:82])[0] / 10.0
                data['grid_frequency'] = struct.unpack('>H', response[82:84])[0] / 100.0
                
                # Calculate totals
                data['total_pv_power'] = data['pv1_power'] + data['pv2_power']
                
                # Load power (this might need adjustment based on actual protocol)
                data['load_power'] = struct.unpack('>H', response[88:90])[0]
                
                # Grid power calculated from power flow
                data['grid_power'] = data['load_power'] - data['total_pv_power'] - data['battery_power']
                
            return data
            
        except Exception as e:
            logger.error(f"Error parsing EG4 response: {e}")
            return None
    
    def collect_data(self):
        """Collect real data from EG4 inverter"""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            # Connect to inverter
            sock.connect((self.inverter_ip, self.inverter_port))
            
            # Send query command (based on our probing)
            query_command = b'\xa1\x01\x00\x00'  # This got good responses
            sock.send(query_command)
            
            # Receive response
            response = sock.recv(4096)
            sock.close()
            
            if response:
                logger.debug(f"Received {len(response)} bytes from inverter")
                data = self.parse_eg4_response(response)
                
                if data:
                    # Update daily totals
                    if data['total_pv_power'] > 0:
                        # Accumulate energy (Wh) = Power (W) * time (h)
                        self.daily_pv_energy += data['total_pv_power'] * self.poll_interval / 3600.0
                        
                    if data['grid_power'] > 0:
                        self.daily_grid_import += data['grid_power'] * self.poll_interval / 3600.0
                    else:
                        self.daily_grid_export += abs(data['grid_power']) * self.poll_interval / 3600.0
                    
                    # Add daily totals to data
                    data['daily_pv_kwh'] = round(self.daily_pv_energy / 1000.0, 2)
                    data['daily_grid_import_kwh'] = round(self.daily_grid_import / 1000.0, 2)
                    data['daily_grid_export_kwh'] = round(self.daily_grid_export / 1000.0, 2)
                    
                    # Add metadata
                    data['timestamp'] = datetime.utcnow().isoformat()
                    data['inverter_mode'] = "Solar/Battery First" if data['total_pv_power'] > 100 else "Grid"
                    
                    logger.info(f"Collected: PV={data['total_pv_power']}W, Battery={data['battery_power']}W ({data['battery_soc']}%), Grid={data['grid_power']}W")
                    return data
                else:
                    logger.warning("Failed to parse EG4 response")
            else:
                logger.warning("No response from inverter")
                
        except socket.timeout:
            logger.warning(f"Connection timeout to {self.inverter_ip}")
        except ConnectionRefusedError:
            logger.error(f"Connection refused by {self.inverter_ip}")
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
        
        return None
    
    def publish_mqtt(self, data):
        """Publish data to MQTT in Solar Assistant format"""
        if not self.mqtt_client:
            return
            
        try:
            # Publish individual topics
            topics = {
                f"{self.mqtt_prefix}/inverter_1/mode": data.get('inverter_mode', 'Unknown'),
                f"{self.mqtt_prefix}/inverter_1/pv1_power": data.get('pv1_power', 0),
                f"{self.mqtt_prefix}/inverter_1/pv2_power": data.get('pv2_power', 0),
                f"{self.mqtt_prefix}/inverter_1/pv_total_power": data.get('total_pv_power', 0),
                f"{self.mqtt_prefix}/inverter_1/battery_voltage": data.get('battery_voltage', 0),
                f"{self.mqtt_prefix}/inverter_1/battery_current": data.get('battery_current', 0),
                f"{self.mqtt_prefix}/inverter_1/battery_power": data.get('battery_power', 0),
                f"{self.mqtt_prefix}/inverter_1/battery_soc": data.get('battery_soc', 0),
                f"{self.mqtt_prefix}/inverter_1/grid_voltage": data.get('grid_voltage', 0),
                f"{self.mqtt_prefix}/inverter_1/grid_power": data.get('grid_power', 0),
                f"{self.mqtt_prefix}/inverter_1/load_power": data.get('load_power', 0),
                f"{self.mqtt_prefix}/total/pv_power": data.get('total_pv_power', 0),
                f"{self.mqtt_prefix}/total/battery_power": data.get('battery_power', 0),
                f"{self.mqtt_prefix}/total/grid_power": data.get('grid_power', 0),
                f"{self.mqtt_prefix}/total/load_power": data.get('load_power', 0),
                f"{self.mqtt_prefix}/total/daily_pv_energy": data.get('daily_pv_kwh', 0),
            }
            
            for topic, value in topics.items():
                self.mqtt_client.publish(topic, str(value), retain=True)
                
            # Also publish complete JSON
            self.mqtt_client.publish(
                f"{self.mqtt_prefix}/inverter_1/data",
                json.dumps(data),
                retain=True
            )
            
            logger.debug("Published data to MQTT")
            
        except Exception as e:
            logger.error(f"Failed to publish to MQTT: {e}")
    
    def write_influxdb(self, data):
        """Write data to InfluxDB"""
        if not self.influx_client:
            return
            
        try:
            # Prepare fields
            fields = {
                "pv1_power": float(data.get('pv1_power', 0)),
                "pv2_power": float(data.get('pv2_power', 0)),
                "pv_total_power": float(data.get('total_pv_power', 0)),
                "battery_voltage": float(data.get('battery_voltage', 0)),
                "battery_current": float(data.get('battery_current', 0)),
                "battery_power": float(data.get('battery_power', 0)),
                "battery_soc": float(data.get('battery_soc', 0)),
                "grid_voltage": float(data.get('grid_voltage', 0)),
                "grid_power": float(data.get('grid_power', 0)),
                "load_power": float(data.get('load_power', 0)),
                "daily_pv_energy": float(data.get('daily_pv_kwh', 0)),
                "daily_grid_import": float(data.get('daily_grid_import_kwh', 0)),
                "daily_grid_export": float(data.get('daily_grid_export_kwh', 0))
            }
            
            json_body = [{
                "measurement": "inverter_data",
                "tags": {
                    "inverter": "eg4_18kpv",
                    "location": "main",
                    "serial": data.get('inverter_serial', 'unknown')
                },
                "time": data['timestamp'],
                "fields": fields
            }]
            
            self.influx_client.write_points(json_body)
            logger.debug("Wrote data to InfluxDB")
            
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
    
    def save_latest(self, data):
        """Save latest data to file for web interface"""
        try:
            # Format for web interface
            web_data = {
                "timestamp": data['timestamp'],
                "inverter": {
                    "mode": data.get('inverter_mode', 'Unknown'),
                    "temperature_c": 35.0  # Placeholder
                },
                "pv": {
                    "total_power_w": data.get('total_pv_power', 0),
                    "pv1_power_w": data.get('pv1_power', 0),
                    "pv2_power_w": data.get('pv2_power', 0),
                    "daily_energy_kwh": data.get('daily_pv_kwh', 0)
                },
                "battery": {
                    "voltage_v": data.get('battery_voltage', 0),
                    "current_a": data.get('battery_current', 0),
                    "power_w": data.get('battery_power', 0),
                    "soc_percent": data.get('battery_soc', 0),
                    "charge_rate_percent_per_hour": abs(data.get('battery_current', 0) * 100 / 200) if data.get('battery_current', 0) < 0 else 0
                },
                "grid": {
                    "voltage_v": data.get('grid_voltage', 0),
                    "power_w": data.get('grid_power', 0),
                    "daily_import_kwh": data.get('daily_grid_import_kwh', 0),
                    "daily_export_kwh": data.get('daily_grid_export_kwh', 0)
                },
                "load": {
                    "power_w": data.get('load_power', 0)
                }
            }
            
            with open('/tmp/solar_assistant_latest.json', 'w') as f:
                json.dump(web_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save latest data: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting Solar Assistant Data Collector (Real EG4 Version)")
        logger.info(f"Inverter: {self.inverter_ip}:{self.inverter_port}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        # Reset daily totals at midnight
        last_reset_day = datetime.now().day
        
        while True:
            try:
                # Check if we need to reset daily totals
                current_day = datetime.now().day
                if current_day != last_reset_day:
                    self.daily_pv_energy = 0.0
                    self.daily_grid_export = 0.0
                    self.daily_grid_import = 0.0
                    last_reset_day = current_day
                    logger.info("Reset daily totals")
                
                # Collect data
                data = self.collect_data()
                
                if data:
                    # Publish to MQTT
                    self.publish_mqtt(data)
                    
                    # Write to InfluxDB
                    self.write_influxdb(data)
                    
                    # Save for web interface
                    self.save_latest(data)
                    
                    self.last_pv_power = data.get('total_pv_power', 0)
                else:
                    logger.warning("No data collected, will retry...")
                
                # Wait for next poll
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Stopping collector...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(self.poll_interval)

if __name__ == "__main__":
    collector = SolarAssistantCollector()
    collector.run()