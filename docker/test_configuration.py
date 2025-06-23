#!/usr/bin/env python3
"""
Test script for Solar Assistant configuration functionality
"""

import requests
import json
import time

BASE_URL = "http://172.16.106.10:9500"

def test_configuration_page():
    """Test the configuration page loads"""
    print("Testing configuration page...")
    response = requests.get(f"{BASE_URL}/configuration")
    if response.status_code == 200:
        print("✓ Configuration page loaded successfully")
        return True
    else:
        print(f"✗ Configuration page failed: {response.status_code}")
        return False

def test_save_inverter_config():
    """Test saving inverter configuration"""
    print("Testing inverter configuration save...")
    
    config_data = {
        'inverter_ip': '172.16.107.129',
        'inverter_port': '8000',
        'inverter_type': 'eg4_18kpv',
        'connection_type': 'network',
        'poll_interval': '5'
    }
    
    response = requests.post(f"{BASE_URL}/api/configuration/inverter", data=config_data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✓ Inverter configuration saved successfully")
            return True
        else:
            print(f"✗ Inverter configuration save failed: {result.get('error')}")
            return False
    else:
        print(f"✗ Inverter configuration request failed: {response.status_code}")
        return False

def test_connection_test():
    """Test inverter connection test"""
    print("Testing inverter connection test...")
    
    config_data = {
        'inverter_ip': '172.16.107.129',
        'inverter_port': '8000'
    }
    
    response = requests.post(f"{BASE_URL}/api/test-connection", data=config_data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✓ Inverter connection test successful")
            return True
        else:
            print(f"✗ Inverter connection test failed: {result.get('error')}")
            return False
    else:
        print(f"✗ Connection test request failed: {response.status_code}")
        return False

def test_save_site_config():
    """Test saving site configuration"""
    print("Testing site configuration save...")
    
    config_data = {
        'site_owner': 'Test Owner'
    }
    
    response = requests.post(
        f"{BASE_URL}/api/configuration/site", 
        json=config_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✓ Site configuration saved successfully")
            return True
        else:
            print(f"✗ Site configuration save failed: {result.get('error')}")
            return False
    else:
        print(f"✗ Site configuration request failed: {response.status_code}")
        return False

def test_api_status():
    """Test status API"""
    print("Testing status API...")
    
    response = requests.get(f"{BASE_URL}/api/status")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Status API working: connected={result.get('connected')}")
        return True
    else:
        print(f"✗ Status API failed: {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("Solar Assistant Configuration Test Suite")
    print("=" * 50)
    
    tests = [
        test_configuration_page,
        test_save_inverter_config,
        test_connection_test,
        test_save_site_config,
        test_api_status
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} error: {e}")
            failed += 1
        
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Configuration functionality is working.")
    else:
        print("⚠️ Some tests failed. Check the configuration implementation.")

if __name__ == '__main__':
    main()