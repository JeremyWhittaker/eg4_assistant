#!/usr/bin/env python3
"""
Modbus client for inverters supporting Modbus TCP/RTU
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
import logging

logger = logging.getLogger(__name__)

class ModbusInverterClient:
    """Generic Modbus client for solar inverters"""
    
    # Common Modbus registers (can be overridden per model)
    REGISTERS = {
        'pv1_voltage': {'address': 0x0000, 'length': 1, 'scale': 0.1},
        'pv1_current': {'address': 0x0001, 'length': 1, 'scale': 0.1},
        'pv1_power': {'address': 0x0002, 'length': 2, 'scale': 1},
        'pv2_voltage': {'address': 0x0004, 'length': 1, 'scale': 0.1},
        'pv2_current': {'address': 0x0005, 'length': 1, 'scale': 0.1},
        'pv2_power': {'address': 0x0006, 'length': 2, 'scale': 1},
        'battery_voltage': {'address': 0x0100, 'length': 1, 'scale': 0.1},
        'battery_current': {'address': 0x0101, 'length': 1, 'scale': 0.1, 'signed': True},
        'battery_power': {'address': 0x0102, 'length': 2, 'scale': 1, 'signed': True},
        'battery_soc': {'address': 0x0104, 'length': 1, 'scale': 1},
        'battery_temp': {'address': 0x0105, 'length': 1, 'scale': 0.1},
        'grid_voltage': {'address': 0x0200, 'length': 1, 'scale': 0.1},
        'grid_frequency': {'address': 0x0201, 'length': 1, 'scale': 0.01},
        'grid_power': {'address': 0x0202, 'length': 2, 'scale': 1, 'signed': True},
        'load_power': {'address': 0x0300, 'length': 2, 'scale': 1},
        'inverter_temp': {'address': 0x0400, 'length': 1, 'scale': 0.1},
        'status': {'address': 0x0500, 'length': 1, 'scale': 1},
    }
    
    # Model-specific register maps
    MODEL_REGISTERS = {
        'eg4_6500ex': {
            # EG4 6500EX-48 specific registers
            'pv1_voltage': {'address': 0x0107, 'length': 1, 'scale': 0.1},
            'pv1_current': {'address': 0x0108, 'length': 1, 'scale': 0.1},
            'battery_voltage': {'address': 0x0101, 'length': 1, 'scale': 0.1},
            'battery_soc': {'address': 0x0100, 'length': 1, 'scale': 1},
        },
        'luxpower': {
            # LuxPower specific registers
            'pv1_voltage': {'address': 0x0A00, 'length': 1, 'scale': 0.1},
            'pv1_current': {'address': 0x0A01, 'length': 1, 'scale': 0.1},
            'battery_voltage': {'address': 0x0B00, 'length': 1, 'scale': 0.1},
            'battery_soc': {'address': 0x0B0C, 'length': 1, 'scale': 1},
        }
    }
    
    def __init__(self, host, port=502, slave_id=1, model=None):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.model = model
        self.client = None
        
        # Use model-specific registers if available
        if model and model in self.MODEL_REGISTERS:
            self.registers = {**self.REGISTERS, **self.MODEL_REGISTERS[model]}
        else:
            self.registers = self.REGISTERS
    
    def connect(self):
        """Connect to Modbus device"""
        try:
            self.client = ModbusTcpClient(self.host, port=self.port)
            if self.client.connect():
                logger.info(f"Connected to Modbus device at {self.host}:{self.port}")
                return True
            else:
                logger.error(f"Failed to connect to {self.host}:{self.port}")
                return False
        except Exception as e:
            logger.error(f"Modbus connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Modbus device"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Modbus device")
    
    def read_data(self):
        """Read all data from inverter"""
        if not self.client or not self.client.is_socket_open():
            logger.error("Not connected to Modbus device")
            return None
        
        data = {}
        
        for key, config in self.registers.items():
            try:
                # Read registers
                result = self.client.read_holding_registers(
                    address=config['address'],
                    count=config['length'],
                    slave=self.slave_id
                )
                
                if not result.isError():
                    # Decode value
                    if config['length'] == 1:
                        value = result.registers[0]
                    else:
                        # Multi-register value (32-bit)
                        decoder = BinaryPayloadDecoder.fromRegisters(
                            result.registers,
                            byteorder=Endian.BIG,
                            wordorder=Endian.BIG
                        )
                        if config.get('signed', False):
                            value = decoder.decode_32bit_int()
                        else:
                            value = decoder.decode_32bit_uint()
                    
                    # Apply scaling
                    value = value * config.get('scale', 1)
                    
                    # Handle signed values for single registers
                    if config['length'] == 1 and config.get('signed', False) and value > 32767:
                        value = value - 65536
                    
                    data[key] = round(value, 2)
                else:
                    logger.warning(f"Error reading {key}: {result}")
                    
            except Exception as e:
                logger.error(f"Error reading {key}: {e}")
        
        # Calculate total PV power
        if 'pv1_power' in data and 'pv2_power' in data:
            data['pv_power'] = data['pv1_power'] + data['pv2_power']
        elif 'pv1_voltage' in data and 'pv1_current' in data:
            data['pv1_power'] = round(data['pv1_voltage'] * data['pv1_current'], 0)
            if 'pv2_voltage' in data and 'pv2_current' in data:
                data['pv2_power'] = round(data['pv2_voltage'] * data['pv2_current'], 0)
                data['pv_power'] = data['pv1_power'] + data['pv2_power']
            else:
                data['pv_power'] = data['pv1_power']
        
        # Decode status
        if 'status' in data:
            data['status_text'] = self._decode_status(int(data['status']))
        
        return data
    
    def _decode_status(self, status_code):
        """Decode status code to text"""
        status_map = {
            0: 'Standby',
            1: 'Grid mode',
            2: 'Battery mode',
            3: 'Fault',
            4: 'Bypass mode',
            5: 'Charging',
            6: 'No connection'
        }
        return status_map.get(status_code, f'Unknown ({status_code})')
    
    def write_register(self, address, value):
        """Write a single register"""
        if not self.client or not self.client.is_socket_open():
            logger.error("Not connected to Modbus device")
            return False
        
        try:
            result = self.client.write_register(address, value, slave=self.slave_id)
            return not result.isError()
        except Exception as e:
            logger.error(f"Error writing register {address}: {e}")
            return False
    
    def set_battery_charge_current(self, current):
        """Set battery charge current (example control function)"""
        # This would need to be implemented based on specific inverter registers
        register_address = 0x0E05  # Example address
        value = int(current * 10)  # Convert to scaled value
        return self.write_register(register_address, value)


# Specific implementations for different inverter models
class EG4ModbusClient(ModbusInverterClient):
    """EG4 specific Modbus implementation"""
    
    def __init__(self, host, port=502, slave_id=1):
        super().__init__(host, port, slave_id, model='eg4_6500ex')


class LuxPowerModbusClient(ModbusInverterClient):
    """LuxPower specific Modbus implementation"""
    
    def __init__(self, host, port=502, slave_id=1):
        super().__init__(host, port, slave_id, model='luxpower')