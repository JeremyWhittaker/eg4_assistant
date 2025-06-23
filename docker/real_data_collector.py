#!/usr/bin/env python3
import paramiko
import json
import time
import threading
import os
from datetime import datetime

class RealDataCollector:
    def __init__(self):
        self.host = os.environ.get('SOLAR_ASSISTANT_HOST', '172.16.106.13')
        self.username = os.environ.get('SOLAR_ASSISTANT_USER', 'solar-assistant')
        self.password = os.environ.get('SOLAR_ASSISTANT_PASS', 'solar123')
        self.data = {}
        self.running = False
        self.error = None
        
    def run_ssh_command(self, ssh, command, use_sudo=False):
        """Run command via SSH and return output"""
        if use_sudo:
            command = f"echo '{self.password}' | sudo -S {command}"
        
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode('utf-8')
        return output
    
    def collect_data(self):
        """Collect data from Solar Assistant InfluxDB"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(self.host, username=self.username, password=self.password)
            
            # Define measurements to extract
            measurements = [
                ("Battery power", "battery_power", "W"),
                ("Battery voltage", "battery_voltage", "V"),
                ("Battery current", "battery_current", "A"),
                ("Battery state of charge", "battery_soc", "%"),
                ("Battery temperature", "battery_temp", "°C"),
                ("Grid power", "grid_power", "W"),
                ("Grid voltage", "grid_voltage", "V"),
                ("Grid frequency", "grid_frequency", "Hz"),
                ("PV power", "pv_power", "W"),
                ("PV power 1", "pv1_power", "W"),
                ("PV power 2", "pv2_power", "W"),
                ("PV voltage 1", "pv1_voltage", "V"),
                ("PV voltage 2", "pv2_voltage", "V"),
                ("Load power", "load_power", "W"),
                ("Load power essential", "load_power_essential", "W"),
                ("Load power non-essential", "load_power_nonessential", "W"),
                ("AC output voltage", "ac_output_voltage", "V"),
                ("Inverter temperature", "inverter_temp", "°C")
            ]
            
            new_data = {}
            for measurement, key, unit in measurements:
                cmd = f"influx -database solar_assistant -execute 'SELECT * FROM \"{measurement}\" ORDER BY time DESC LIMIT 1' -format json"
                output = self.run_ssh_command(ssh, cmd, use_sudo=True)
                
                try:
                    result = json.loads(output)
                    if result["results"][0].get("series"):
                        series = result["results"][0]["series"][0]
                        values = series["values"][0]
                        
                        # Get the field value
                        if "combined" in series["columns"]:
                            idx = series["columns"].index("combined")
                            value = values[idx]
                        elif "inverter_0" in series["columns"]:
                            idx = series["columns"].index("inverter_0")
                            value = values[idx]
                        else:
                            continue
                        
                        new_data[key] = {
                            "value": value,
                            "unit": unit
                        }
                except:
                    pass
            
            # Calculate additional values
            if "battery_power" in new_data:
                battery_power = new_data["battery_power"]["value"]
                if battery_power < 0:
                    new_data["battery_status"] = "charging"
                    new_data["battery_charge_power"] = abs(battery_power)
                else:
                    new_data["battery_status"] = "discharging"
                    new_data["battery_discharge_power"] = battery_power
            
            # Determine system mode
            pv_power = new_data.get("pv_power", {}).get("value", 0)
            grid_power = new_data.get("grid_power", {}).get("value", 0)
            battery_power = new_data.get("battery_power", {}).get("value", 0)
            
            if pv_power > 100:
                new_data["system_mode"] = "Solar"
            elif grid_power < -100:
                new_data["system_mode"] = "Grid Export"
            elif battery_power > 100:
                new_data["system_mode"] = "Battery"
            else:
                new_data["system_mode"] = "Grid"
            
            new_data["timestamp"] = datetime.now().isoformat()
            
            self.data = new_data
            self.error = None
            
            ssh.close()
            return True
            
        except Exception as e:
            self.error = str(e)
            ssh.close()
            return False
    
    def start(self):
        """Start the data collection thread"""
        self.running = True
        self.thread = threading.Thread(target=self._collect_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the data collection thread"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
    
    def _collect_loop(self):
        """Main collection loop"""
        while self.running:
            self.collect_data()
            time.sleep(5)  # Update every 5 seconds
    
    def get_data(self):
        """Get the latest data"""
        if self.error:
            return {"error": self.error}
        return self.data

if __name__ == "__main__":
    # Test the collector
    collector = RealDataCollector()
    if collector.collect_data():
        print("Data collected successfully:")
        print(json.dumps(collector.get_data(), indent=2))
    else:
        print(f"Error: {collector.error}")