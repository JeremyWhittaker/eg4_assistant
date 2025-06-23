#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")

# Check connection
print(ssh.exec_command("netstat -tn | grep 172.16.107.129:8000")[1].read().decode())

# Get latest values
cmd = """sudo influx -database solar_assistant -execute 'SELECT last(*) FROM "Battery power", "Grid power", "PV power" WHERE time > now() - 30s' -format csv 2>/dev/null | grep -v name"""
print("\nLatest values:")
print(ssh.exec_command(cmd)[1].read().decode())

ssh.close()