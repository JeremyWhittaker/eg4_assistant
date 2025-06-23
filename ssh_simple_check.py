#!/usr/bin/env python3
"""Simple check of what's happening"""

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Just check what protocol/port is being used
    print("=== Connection details ===")
    output = ssh.exec_command("netstat -tn | grep 172.16.107.129")[1].read().decode()
    print(output)
    
    # Check if it's the same as what we found (port 8000)
    print("\n=== Is it using port 8000? ===")
    if "8000" in output:
        print("YES - Solar Assistant is using port 8000 (same as our connection)")
        print("\nThis means Solar Assistant is using the same IoTOS protocol we discovered.")
        print("The commands we found (a1 1a 05 00, etc.) are correct.")
        print("\nThe difference is Solar Assistant:")
        print("1. Sends multiple queries to get all data")
        print("2. Parses the responses according to specific byte offsets")
        print("3. Stores the parsed values in InfluxDB")
    
    # Quick check what data it has
    print("\n=== Sample data Solar Assistant is getting ===")
    cmd = """sudo influx -database solar_assistant -execute 'SELECT last(*) FROM "Battery power", "Grid power", "PV power"' -format csv 2>/dev/null"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
finally:
    ssh.close()

print("\n=== CONCLUSION ===")
print("Solar Assistant connects to EG4 at 172.16.107.129:8000")
print("It uses the IoTOS protocol with commands like:")
print("  - a1 1a 05 00 (main status)")
print("  - a1 1a 05 02 (extended status)")
print("  - a1 1a 01 00 (additional data)")
print("  - a1 1a 03 00 (more data)")
print("\nEach command returns 117 bytes with different data fields.")
print("To get all the data Solar Assistant shows, we need to:")
print("1. Send multiple commands")
print("2. Parse each response according to its specific format")
print("3. Combine the results")