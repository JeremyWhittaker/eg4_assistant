#!/usr/bin/env python3
"""
Modbus TCP Data Collector for EG4 18kPV Inverter
Based on Solar Assistant's approach using Modbus TCP on port 8000
"""

import time
import json
import logging
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from config_watcher import ConfigWatcher
import shared_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModbusDataCollector:
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
        
        # Modbus client
        self.client = None
        self.connected = False
        
        # EG4 18kPV Modbus registers (based on documentation)
        self.registers = {
            # PV Input
            'pv1_voltage': {'addr': 109, 'count': 1, 'scale': 0.1},
            'pv1_current': {'addr': 110, 'count': 1, 'scale': 0.01},
            'pv1_power': {'addr': 111, 'count': 2, 'scale': 1},
            'pv2_voltage': {'addr': 113, 'count': 1, 'scale': 0.1},
            'pv2_current': {'addr': 114, 'count': 1, 'scale': 0.01},
            'pv2_power': {'addr': 115, 'count': 2, 'scale': 1},
            'pv3_voltage': {'addr': 117, 'count': 1, 'scale': 0.1},
            'pv3_current': {'addr': 118, 'count': 1, 'scale': 0.01},
            'pv3_power': {'addr': 119, 'count': 2, 'scale': 1},
            
            # Battery
            'battery_voltage': {'addr': 157, 'count': 1, 'scale': 0.01},
            'battery_current': {'addr': 158, 'count': 1, 'scale': 0.01, 'signed': True},
            'battery_power': {'addr': 159, 'count': 2, 'scale': 1, 'signed': True},
            'battery_soc': {'addr': 161, 'count': 1, 'scale': 1},
            'battery_temp': {'addr': 162, 'count': 1, 'scale': 0.1, 'signed': True},
            
            # Grid
            'grid_voltage': {'addr': 150, 'count': 1, 'scale': 0.1},
            'grid_frequency': {'addr': 151, 'count': 1, 'scale': 0.01},
            'grid_power': {'addr': 152, 'count': 2, 'scale': 1, 'signed': True},
            
            # Load
            'load_power': {'addr': 154, 'count': 2, 'scale': 1},
            
            # Inverter
            'inverter_temp': {'addr': 163, 'count': 1, 'scale': 0.1},
            
            # Energy
            'today_energy': {'addr': 201, 'count': 2, 'scale': 0.1},
        }
        
        logger.info(f"Modbus Data Collector initialized - IP: {self.inverter_ip}, Port: {self.inverter_port}")
        
    def on_config_change(self, old_config, new_config, changed_keys):
        """Handle configuration changes"""
        logger.info(f"Configuration changed: {changed_keys}")
        
        if 'inverter_ip' in changed_keys or 'inverter_port' in changed_keys:
            self.inverter_ip = new_config.get('inverter_ip', '172.16.107.129')
            self.inverter_port = new_config.get('inverter_port', 8000)
            logger.info(f"Reconnecting to {self.inverter_ip}:{self.inverter_port}")
            self.disconnect()
            
        if 'poll_interval' in changed_keys:
            self.poll_interval = new_config.get('poll_interval', 5)
            logger.info(f"Poll interval changed to: {self.poll_interval}")
    
    def connect(self):
        """Connect to inverter via Modbus TCP"""
        try:
            if self.client:
                self.client.close()
                
            self.client = ModbusTcpClient(
                self.inverter_ip,
                port=self.inverter_port,
                timeout=5,
                retries=3,
                retry_on_empty=True
            )
            
            self.connected = self.client.connect()
            if self.connected:
                logger.info(f"Connected to inverter at {self.inverter_ip}:{self.inverter_port}")
            else:
                logger.error(f"Failed to connect to inverter at {self.inverter_ip}:{self.inverter_port}")
                
            return self.connected
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from inverter"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from inverter")
    
    def read_register_value(self, name, config):
        """Read a value from Modbus registers"""
        try:
            if not self.connected:
                return None
                
            # Read holding registers
            result = self.client.read_holding_registers(
                config['addr'],
                config['count'],
                slave=1  # EG4 uses slave ID 1
            )
            
            if result.isError():
                logger.error(f"Error reading {name}: {result}")
                return None
                
            # Decode value based on register count
            if config['count'] == 1:
                value = result.registers[0]
                if config.get('signed', False) and value > 32767:
                    value = value - 65536
            else:  # 32-bit value
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers,
                    byteorder=Endian.BIG,
                    wordorder=Endian.BIG
                )
                if config.get('signed', False):
                    value = decoder.decode_32bit_int()
                else:
                    value = decoder.decode_32bit_uint()
                    
            # Apply scale
            return value * config.get('scale', 1)
            
        except Exception as e:
            logger.error(f"Error reading {name}: {e}")
            return None
    
    def collect_data(self):
        """Collect data from inverter"""
        try:
            if not self.connected:
                if not self.connect():
                    return None
                    
            data = {
                'timestamp': datetime.now().isoformat(),
                'connection_status': 'connected'
            }
            
            # Read all registers
            for name, config in self.registers.items():
                value = self.read_register_value(name, config)
                if value is not None:
                    data[name] = value
                    
            # Calculate total PV power
            data['pv_power_total'] = (
                data.get('pv1_power', 0) + 
                data.get('pv2_power', 0) + 
                data.get('pv3_power', 0)
            )
            
            # Determine battery state
            battery_current = data.get('battery_current', 0)
            if battery_current > 0.5:
                data['battery_state'] = 'charging'
            elif battery_current < -0.5:
                data['battery_state'] = 'discharging'
            else:
                data['battery_state'] = 'idle'
                
            # Determine grid state
            grid_power = data.get('grid_power', 0)
            if grid_power > 50:
                data['grid_state'] = 'importing'
            elif grid_power < -50:
                data['grid_state'] = 'exporting'
            else:
                data['grid_state'] = 'standby'
                
            logger.info(f"Data collected - PV: {data['pv_power_total']:.0f}W, " +
                       f"Battery: {data.get('battery_power', 0):.0f}W ({data.get('battery_soc', 0)}%), " +
                       f"Load: {data.get('load_power', 0):.0f}W")
                       
            return data
            
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            self.disconnect()
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
        logger.info("Starting Modbus data collection loop")
        consecutive_failures = 0
        
        while True:
            try:
                # Collect data
                data = self.collect_data()
                
                if data:
                    self.publish_data(data)
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    logger.warning(f"Failed to collect data (attempt {consecutive_failures})")
                    
                    # If too many failures, publish error status
                    if consecutive_failures >= 3:
                        error_data = {
                            'timestamp': datetime.now().isoformat(),
                            'connection_status': 'disconnected',
                            'error': 'Cannot connect to inverter'
                        }
                        self.publish_data(error_data)
                        
                    # Exponential backoff on failures
                    if consecutive_failures > 0:
                        wait_time = min(self.poll_interval * (2 ** (consecutive_failures - 1)), 60)
                        time.sleep(wait_time)
                        continue
                
                # Normal poll interval
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down collector")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)
        
        self.disconnect()

if __name__ == '__main__':
    collector = ModbusDataCollector()
    collector.run()