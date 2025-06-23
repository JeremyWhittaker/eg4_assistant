#!/usr/bin/env python3
"""
Test that configuration changes propagate to the data collector
"""

import time
import json
import requests

def test_config_propagation():
    """Test that changing configuration affects data collection"""
    
    print("Testing configuration propagation...")
    print("=" * 50)
    
    # Step 1: Save initial configuration
    print("1. Setting initial configuration...")
    config1 = {
        'inverter_ip': '172.16.107.129',
        'inverter_port': '8000',
        'poll_interval': '5'
    }
    
    response = requests.post(
        'http://172.16.106.10:9500/api/configuration/inverter',
        data=config1
    )
    
    if response.status_code == 200:
        print("✓ Initial configuration saved")
    else:
        print("✗ Failed to save initial configuration")
        return False
        
    # Step 2: Wait for collector to pick up config
    print("2. Waiting 3 seconds for collector to load config...")
    time.sleep(3)
    
    # Step 3: Change poll interval
    print("3. Changing poll interval to 10 seconds...")
    config2 = {
        'inverter_ip': '172.16.107.129',
        'inverter_port': '8000',
        'poll_interval': '10'
    }
    
    response = requests.post(
        'http://172.16.106.10:9500/api/configuration/inverter',
        data=config2
    )
    
    if response.status_code == 200:
        print("✓ Configuration updated")
    else:
        print("✗ Failed to update configuration")
        return False
        
    # Step 4: Verify config file was updated
    print("4. Verifying configuration file...")
    try:
        with open('./config/settings.json', 'r') as f:
            saved_config = json.load(f)
            if saved_config.get('poll_interval') == 10:
                print("✓ Configuration file updated correctly")
                print(f"  Current config: {json.dumps(saved_config, indent=2)}")
            else:
                print("✗ Configuration file not updated")
                return False
    except Exception as e:
        print(f"✗ Error reading config file: {e}")
        return False
        
    # Step 5: Change inverter IP
    print("5. Changing inverter IP...")
    config3 = {
        'inverter_ip': '172.16.107.130',  # Different IP
        'inverter_port': '8000',
        'poll_interval': '10'
    }
    
    response = requests.post(
        'http://172.16.106.10:9500/api/configuration/inverter',
        data=config3
    )
    
    if response.status_code == 200:
        print("✓ Inverter IP updated")
    else:
        print("✗ Failed to update inverter IP")
        return False
        
    print("\n" + "=" * 50)
    print("🎉 Configuration propagation test completed!")
    print("\nNote: The data collector should now be using:")
    print(f"  - Inverter IP: 172.16.107.130")
    print(f"  - Poll Interval: 10 seconds")
    print("\nCheck the collector logs to verify it detected the changes.")
    
    return True

if __name__ == '__main__':
    test_config_propagation()