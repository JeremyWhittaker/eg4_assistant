#!/usr/bin/env python3
"""
Solar Assistant Compatible Data Collector
Collects data from EG4 18kPV and publishes in Solar Assistant format
"""

import os
import time
import json
import logging
from datetime import datetime
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt
import random
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SolarAssistantCollector:
    def __init__(self):
        # Settings
        self.inverter_ip = os.environ.get('INVERTER_IP', '172.16.107.129')
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
        
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client = mqtt.Client(client_id='solar_assistant_collector')
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            self.mqtt_client = None
            
    def connect_influxdb(self):
        """Connect to InfluxDB"""
        try:
            self.influx_client = InfluxDBClient(
                host=self.influx_host,
                port=self.influx_port,
                database=self.influx_db
            )
            
            # Create database if needed
            dbs = self.influx_client.get_list_database()
            if not any(db['name'] == self.influx_db for db in dbs):
                self.influx_client.create_database(self.influx_db)
                
            logger.info("Connected to InfluxDB")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            self.influx_client = None
    
    def collect_data(self):
        """Collect data - using realistic simulation for now"""
        # Note: Real EG4 connection will be implemented once protocol is confirmed
        
        hour = datetime.now().hour
        minute = datetime.now().minute
        
        # Simulate realistic solar curve
        time_decimal = hour + minute / 60.0
        solar_factor = 0
        if 6 <= time_decimal <= 18:
            # Bell curve peaking at noon
            solar_factor = math.sin((time_decimal - 6) * math.pi / 12)
            # Add some clouds
            solar_factor *= (0.8 + 0.2 * random.random())
        
        # Generate realistic values
        pv_max = 18000  # 18kW max for EG4 18kPV
        pv_power = int(pv_max * solar_factor) + random.randint(-200, 200)
        pv_power = max(0, pv_power)
        
        # Individual PV strings (3 MPPTs)
        pv1_power = int(pv_power * 0.35)
        pv2_power = int(pv_power * 0.35)
        pv3_power = int(pv_power * 0.30)
        
        # Battery behavior
        battery_soc = 50 + int(30 * math.sin(time_decimal * math.pi / 24)) + random.randint(-5, 5)
        battery_soc = max(20, min(95, battery_soc))
        
        # Battery charges during day, discharges at night
        if pv_power > 3000 and battery_soc < 90:
            battery_power = -min(pv_power * 0.4, 8000)  # Charging (negative)
        elif pv_power < 500 and battery_soc > 30:
            battery_power = 2000 + random.randint(-500, 500)  # Discharging
        else:
            battery_power = random.randint(-200, 200)
        
        # Load varies throughout day
        base_load = 2000
        if 7 <= hour <= 9 or 17 <= hour <= 21:
            base_load = 4000  # Peak hours
        load_power = base_load + random.randint(-500, 500)
        
        # Grid makes up the difference
        grid_power = load_power - pv_power - battery_power
        
        # Battery voltage based on SOC
        battery_voltage = 48.0 + (battery_soc / 100.0) * 6.0
        battery_current = battery_power / battery_voltage
        
        # Grid voltage
        grid_voltage = 240.0 + random.uniform(-2, 2)
        
        # Update daily totals
        self.daily_pv_energy += pv_power * self.poll_interval / 3600000.0  # kWh
        if grid_power < 0:
            self.daily_grid_export += abs(grid_power) * self.poll_interval / 3600000.0
        else:
            self.daily_grid_import += grid_power * self.poll_interval / 3600000.0
        
        # Build data structure matching Solar Assistant format
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": "BA32401949",
            "inverter": {
                "status": "ok",
                "mode": "Solar/Grid mode" if pv_power > 100 else "Grid mode",
                "output_power_w": load_power,
                "output_voltage_v": grid_voltage,
                "frequency_hz": 60.0,
                "temperature_c": 35.0 + random.uniform(-5, 10)
            },
            "battery": {
                "soc_percent": battery_soc,
                "voltage_v": battery_voltage,
                "current_a": battery_current,
                "power_w": battery_power,
                "temperature_c": 25.0 + random.uniform(-2, 5),
                "charge_rate_percent_per_hour": (battery_current * 100.0 / 200.0) if battery_power < 0 else 0
            },
            "grid": {
                "voltage_v": grid_voltage,
                "frequency_hz": 60.0,
                "power_w": grid_power,
                "current_a": grid_power / grid_voltage,
                "connected": True
            },
            "pv": {
                "pv1_voltage_v": 380.0 + random.uniform(-20, 20) if pv1_power > 0 else 0,
                "pv1_current_a": pv1_power / 380.0 if pv1_power > 0 else 0,
                "pv1_power_w": pv1_power,
                "pv2_voltage_v": 385.0 + random.uniform(-20, 20) if pv2_power > 0 else 0,
                "pv2_current_a": pv2_power / 385.0 if pv2_power > 0 else 0,
                "pv2_power_w": pv2_power,
                "pv3_voltage_v": 375.0 + random.uniform(-20, 20) if pv3_power > 0 else 0,
                "pv3_current_a": pv3_power / 375.0 if pv3_power > 0 else 0,
                "pv3_power_w": pv3_power,
                "total_power_w": pv_power,
                "daily_energy_kwh": round(self.daily_pv_energy, 2)
            },
            "load": {
                "power_w": load_power,
                "percentage": int(load_power * 100 / 18000)
            },
            "totals": {
                "daily_pv_kwh": round(self.daily_pv_energy, 2),
                "daily_grid_export_kwh": round(self.daily_grid_export, 2),
                "daily_grid_import_kwh": round(self.daily_grid_import, 2)
            }
        }
        
        return data
    
    def publish_mqtt(self, data):
        """Publish data to MQTT in Solar Assistant format"""
        if not self.mqtt_client:
            return
            
        try:
            # Publish complete state
            topic = f"{self.mqtt_prefix}/state"
            self.mqtt_client.publish(topic, json.dumps(data), retain=True)
            
            # Publish individual metrics
            metrics = {
                f"inverter/power": data["inverter"]["output_power_w"],
                f"inverter/voltage": data["inverter"]["output_voltage_v"],
                f"inverter/mode": data["inverter"]["mode"],
                f"battery/soc": data["battery"]["soc_percent"],
                f"battery/voltage": data["battery"]["voltage_v"],
                f"battery/power": data["battery"]["power_w"],
                f"grid/voltage": data["grid"]["voltage_v"],
                f"grid/power": data["grid"]["power_w"],
                f"pv/total_power": data["pv"]["total_power_w"],
                f"pv/daily_energy": data["pv"]["daily_energy_kwh"],
                f"load/power": data["load"]["power_w"]
            }
            
            for metric, value in metrics.items():
                topic = f"{self.mqtt_prefix}/{metric}"
                self.mqtt_client.publish(topic, str(value), retain=True)
                
            logger.info(f"Published to MQTT: PV={data['pv']['total_power_w']}W, Battery={data['battery']['power_w']}W, Grid={data['grid']['power_w']}W")
            
        except Exception as e:
            logger.error(f"Failed to publish to MQTT: {e}")
    
    def write_influxdb(self, data):
        """Write data to InfluxDB"""
        if not self.influx_client:
            return
            
        try:
            # Flatten the nested structure for InfluxDB
            fields = {
                "pv1_power": data["pv"]["pv1_power_w"],
                "pv2_power": data["pv"]["pv2_power_w"],
                "pv3_power": data["pv"]["pv3_power_w"],
                "total_pv_power": data["pv"]["total_power_w"],
                "battery_power": data["battery"]["power_w"],
                "battery_soc": data["battery"]["soc_percent"],
                "battery_voltage": data["battery"]["voltage_v"],
                "grid_power": data["grid"]["power_w"],
                "grid_voltage": data["grid"]["voltage_v"],
                "load_power": data["load"]["power_w"],
                "daily_pv_energy": data["pv"]["daily_energy_kwh"],
                "inverter_temp": data["inverter"]["temperature_c"],
                "battery_temp": data["battery"]["temperature_c"]
            }
            
            json_body = [{
                "measurement": "inverter_data",
                "tags": {
                    "inverter": "eg4_18kpv",
                    "device_id": data["device_id"],
                    "location": "main"
                },
                "time": data["timestamp"],
                "fields": fields
            }]
            
            self.influx_client.write_points(json_body)
            
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
    
    def run(self):
        """Main collection loop"""
        logger.info("Starting Solar Assistant Compatible Collector...")
        logger.info(f"Inverter: {self.inverter_ip} (simulated data)")
        logger.info(f"MQTT: {self.mqtt_host}:{self.mqtt_port}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        # Reset daily totals at midnight
        last_reset_day = datetime.now().day
        
        while True:
            try:
                # Reset daily totals at midnight
                current_day = datetime.now().day
                if current_day != last_reset_day:
                    self.daily_pv_energy = 0.0
                    self.daily_grid_export = 0.0
                    self.daily_grid_import = 0.0
                    last_reset_day = current_day
                
                # Collect data
                data = self.collect_data()
                
                if data:
                    # Publish to MQTT
                    self.publish_mqtt(data)
                    
                    # Write to InfluxDB
                    self.write_influxdb(data)
                    
                    # Save latest data for web interface
                    with open('/tmp/solar_assistant_latest.json', 'w') as f:
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
    collector = SolarAssistantCollector()
    collector.run()