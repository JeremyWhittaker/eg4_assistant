#!/usr/bin/env python3
"""Test real data collection from Solar Assistant"""

import os
import json
from real_data_collector import RealDataCollector

# Set environment variables for testing
os.environ['SOLAR_ASSISTANT_HOST'] = '172.16.109.214'
os.environ['SOLAR_ASSISTANT_USER'] = 'solar-assistant'  
os.environ['SOLAR_ASSISTANT_PASS'] = 'solar123'

def test_real_data():
    print("Testing Real Data Collection from Solar Assistant")
    print("="*50)
    
    collector = RealDataCollector()
    
    print(f"Connecting to {collector.host}...")
    
    # Test single collection
    if collector.collect_data():
        print("\nData collected successfully!")
        print("\nCurrent Values:")
        print("-"*30)
        
        data = collector.get_data()
        
        # Display key values
        if 'battery_power' in data:
            print(f"Battery Power: {data['battery_power']['value']} {data['battery_power']['unit']}")
        if 'battery_soc' in data:
            print(f"Battery SOC: {data['battery_soc']['value']} {data['battery_soc']['unit']}")
        if 'battery_voltage' in data:
            print(f"Battery Voltage: {data['battery_voltage']['value']} {data['battery_voltage']['unit']}")
        if 'grid_power' in data:
            print(f"Grid Power: {data['grid_power']['value']} {data['grid_power']['unit']}")
        if 'grid_voltage' in data:
            print(f"Grid Voltage: {data['grid_voltage']['value']} {data['grid_voltage']['unit']}")
        if 'pv_power' in data:
            print(f"PV Power: {data['pv_power']['value']} {data['pv_power']['unit']}")
        if 'load_power' in data:
            print(f"Load Power: {data['load_power']['value']} {data['load_power']['unit']}")
        if 'inverter_temp' in data:
            print(f"Inverter Temp: {data['inverter_temp']['value']} {data['inverter_temp']['unit']}")
            
        print(f"\nSystem Mode: {data.get('system_mode', 'Unknown')}")
        print(f"Battery Status: {data.get('battery_status', 'Unknown')}")
        
        # Save full data
        with open('test_real_data_output.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("\nFull data saved to test_real_data_output.json")
        
    else:
        print(f"\nError collecting data: {collector.error}")

if __name__ == "__main__":
    test_real_data()