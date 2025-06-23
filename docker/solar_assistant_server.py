#!/usr/bin/env python3
"""
Solar Assistant Server - Docker Version
Complete solar monitoring system with web interface
"""

import os
import sys
import yaml
import logging
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# Load configuration
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config/config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Setup logging
LOG_PATH = os.environ.get('LOG_PATH', '/data/logs')
os.makedirs(LOG_PATH, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format=config['logging']['format'],
    handlers=[
        logging.FileHandler(os.path.join(LOG_PATH, 'solar_assistant.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import our modules
from database import Database
from eg4_iotos_client import EG4IoTOSClient
from modbus_client import ModbusInverterClient as ModbusClient

app = Flask(__name__)
app.config['SECRET_KEY'] = config['web_server']['secret_key']
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
CORS(app)

# Global variables
db = None
inverter_clients = {}
update_thread = None
mqtt_client = None
influx_client = None

@dataclass
class SystemStatus:
    """Overall system status"""
    total_pv_power: float = 0.0
    total_battery_power: float = 0.0
    total_grid_power: float = 0.0
    total_load_power: float = 0.0
    battery_soc: float = 0.0
    grid_status: bool = False
    inverter_count: int = 0
    active_alerts: List[Dict] = None
    last_update: str = ""

    def __post_init__(self):
        if self.active_alerts is None:
            self.active_alerts = []

class SolarAssistantServer:
    def __init__(self):
        self.db = Database(os.environ.get('DATABASE_PATH', '/data/db/solar_assistant.db'))
        self.system_status = SystemStatus()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.running = False
        
    def initialize(self):
        """Initialize the server and all components"""
        logger.info("Initializing Solar Assistant Server...")
        
        # Initialize database
        self.db.initialize()
        
        # Load inverters from config
        self._load_inverters()
        
        # Initialize MQTT if enabled
        if config['mqtt']['enabled']:
            self._init_mqtt()
        
        # Initialize InfluxDB if enabled
        if config['influxdb']['enabled']:
            self._init_influxdb()
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("Solar Assistant Server initialized successfully")
    
    def _load_inverters(self):
        """Load inverter configurations"""
        inverters = config.get('inverters', [])
        
        for inv_config in inverters:
            if not inv_config.get('enabled', True):
                continue
                
            name = inv_config['name']
            inv_type = inv_config['type']
            protocol = inv_config['protocol']
            
            try:
                if protocol == 'iotos' and inv_type == 'eg4_18kpv':
                    client = EG4IoTOSClient(
                        host=inv_config['host'],
                        port=inv_config.get('port', 8000)
                    )
                elif protocol in ['modbus_tcp', 'modbus_rtu']:
                    client = ModbusClient(
                        host=inv_config['host'],
                        port=inv_config.get('port', 502),
                        unit_id=inv_config.get('unit_id', 1)
                    )
                else:
                    logger.warning(f"Unknown protocol {protocol} for inverter {name}")
                    continue
                
                inverter_clients[name] = {
                    'client': client,
                    'config': inv_config,
                    'last_data': None,
                    'last_update': None,
                    'errors': 0
                }
                
                # Add to database
                self.db.add_inverter(
                    name=name,
                    model=inv_type,
                    ip_address=inv_config['host'],
                    port=inv_config.get('port'),
                    protocol=protocol
                )
                
                logger.info(f"Loaded inverter: {name} ({inv_type}, {protocol})")
                
            except Exception as e:
                logger.error(f"Failed to initialize inverter {name}: {e}")
    
    def _init_mqtt(self):
        """Initialize MQTT client"""
        try:
            import paho.mqtt.client as mqtt
            
            self.mqtt_client = mqtt.Client()
            
            if config['mqtt']['username']:
                self.mqtt_client.username_pw_set(
                    config['mqtt']['username'],
                    config['mqtt']['password']
                )
            
            self.mqtt_client.connect(
                config['mqtt']['host'],
                config['mqtt']['port'],
                60
            )
            
            self.mqtt_client.loop_start()
            logger.info("MQTT client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize MQTT: {e}")
    
    def _init_influxdb(self):
        """Initialize InfluxDB client"""
        try:
            from influxdb_client import InfluxDBClient
            
            self.influx_client = InfluxDBClient(
                url=f"http://{config['influxdb']['host']}:{config['influxdb']['port']}",
                token=config['influxdb']['token'],
                org=config['influxdb']['org']
            )
            
            self.influx_write_api = self.influx_client.write_api()
            logger.info("InfluxDB client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB: {e}")
    
    def _start_background_tasks(self):
        """Start all background tasks"""
        self.running = True
        
        # Data collection thread
        threading.Thread(target=self._data_collection_loop, daemon=True).start()
        
        # MQTT publishing thread
        if config['mqtt']['enabled']:
            threading.Thread(target=self._mqtt_publish_loop, daemon=True).start()
        
        # Alert monitoring thread
        if config['alerts']['enabled']:
            threading.Thread(target=self._alert_monitoring_loop, daemon=True).start()
        
        # Cleanup thread
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
    
    def _data_collection_loop(self):
        """Main data collection loop"""
        while self.running:
            try:
                # Collect data from all inverters
                total_pv = 0
                total_battery = 0
                total_grid = 0
                total_load = 0
                battery_soc_sum = 0
                active_count = 0
                
                for name, inverter in inverter_clients.items():
                    try:
                        # Get data from inverter
                        data = inverter['client'].get_realtime_data()
                        
                        if data:
                            inverter['last_data'] = data
                            inverter['last_update'] = datetime.now()
                            inverter['errors'] = 0
                            
                            # Store in database
                            self.db.add_realtime_data(
                                inverter_id=self.db.get_inverter_by_name(name)['id'],
                                data=data
                            )
                            
                            # Update totals
                            total_pv += data.get('pv_power', 0)
                            total_battery += data.get('battery_power', 0)
                            total_grid += data.get('grid_power', 0)
                            total_load += data.get('load_power', 0)
                            battery_soc_sum += data.get('battery_soc', 0)
                            active_count += 1
                            
                            # Write to InfluxDB
                            if self.influx_write_api:
                                self._write_to_influxdb(name, data)
                    
                    except Exception as e:
                        inverter['errors'] += 1
                        logger.error(f"Error collecting data from {name}: {e}")
                
                # Update system status
                self.system_status.total_pv_power = total_pv
                self.system_status.total_battery_power = total_battery
                self.system_status.total_grid_power = total_grid
                self.system_status.total_load_power = total_load
                self.system_status.battery_soc = battery_soc_sum / max(active_count, 1)
                self.system_status.grid_status = total_grid > 0
                self.system_status.inverter_count = active_count
                self.system_status.last_update = datetime.now().isoformat()
                
                # Emit update via WebSocket
                socketio.emit('system_update', asdict(self.system_status))
                
                # Sleep for update interval
                time.sleep(config['system']['update_interval'])
                
            except Exception as e:
                logger.error(f"Error in data collection loop: {e}")
                time.sleep(5)
    
    def _mqtt_publish_loop(self):
        """MQTT publishing loop"""
        while self.running:
            try:
                if self.mqtt_client and self.mqtt_client.is_connected():
                    prefix = config['mqtt']['topics']['prefix']
                    
                    # Publish system status
                    self.mqtt_client.publish(
                        f"{prefix}/system/status",
                        json.dumps(asdict(self.system_status)),
                        qos=config['mqtt']['topics']['qos'],
                        retain=config['mqtt']['topics']['retain']
                    )
                    
                    # Publish individual inverter data
                    for name, inverter in inverter_clients.items():
                        if inverter['last_data']:
                            self.mqtt_client.publish(
                                f"{prefix}/inverter/{name}",
                                json.dumps(inverter['last_data']),
                                qos=config['mqtt']['topics']['qos'],
                                retain=config['mqtt']['topics']['retain']
                            )
                
                time.sleep(config['mqtt']['topics']['publish_interval'])
                
            except Exception as e:
                logger.error(f"Error in MQTT publish loop: {e}")
                time.sleep(10)
    
    def _alert_monitoring_loop(self):
        """Monitor for alert conditions"""
        while self.running:
            try:
                active_alerts = []
                
                for rule in config['alerts']['rules']:
                    # Check condition (simplified)
                    if self._check_alert_condition(rule['condition']):
                        active_alerts.append({
                            'name': rule['name'],
                            'severity': rule['severity'],
                            'timestamp': datetime.now().isoformat()
                        })
                
                self.system_status.active_alerts = active_alerts
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")
                time.sleep(60)
    
    def _check_alert_condition(self, condition):
        """Check if alert condition is met"""
        # Simplified condition checking
        try:
            # Replace variables with actual values
            condition = condition.replace('battery_soc', str(self.system_status.battery_soc))
            condition = condition.replace('grid_status', '1' if self.system_status.grid_status else '0')
            condition = condition.replace('load_percentage', '0')  # TODO: Calculate actual load percentage
            
            return eval(condition)
        except:
            return False
    
    def _cleanup_loop(self):
        """Cleanup old data"""
        while self.running:
            try:
                # Clean up old data
                retention_days = config['system']['data_retention']
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                
                self.db.cleanup_old_data(cutoff_date)
                
                # Run daily
                time.sleep(86400)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(3600)
    
    def _write_to_influxdb(self, inverter_name, data):
        """Write data point to InfluxDB"""
        try:
            from influxdb_client import Point
            
            point = Point("inverter_data") \
                .tag("inverter", inverter_name) \
                .field("pv_power", data.get('pv_power', 0)) \
                .field("battery_power", data.get('battery_power', 0)) \
                .field("grid_power", data.get('grid_power', 0)) \
                .field("load_power", data.get('load_power', 0)) \
                .field("battery_soc", data.get('battery_soc', 0))
            
            self.influx_write_api.write(
                bucket=config['influxdb']['bucket'],
                org=config['influxdb']['org'],
                record=point
            )
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")

# Initialize server
server = SolarAssistantServer()

# Flask routes
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    return jsonify(asdict(server.system_status))

@app.route('/api/inverters')
def api_inverters():
    inverters = []
    for name, inverter in inverter_clients.items():
        inverters.append({
            'name': name,
            'config': inverter['config'],
            'last_data': inverter['last_data'],
            'last_update': inverter['last_update'].isoformat() if inverter['last_update'] else None,
            'errors': inverter['errors']
        })
    return jsonify(inverters)

@app.route('/api/data/<inverter_name>/<period>')
def api_data(inverter_name, period):
    # Get historical data
    hours = {'hour': 1, 'day': 24, 'week': 168, 'month': 720}.get(period, 24)
    start_time = datetime.now() - timedelta(hours=hours)
    
    data = server.db.get_historical_data(inverter_name, start_time)
    return jsonify(data)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        # Update configuration
        new_config = request.json
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(new_config, f)
        return jsonify({'status': 'success', 'message': 'Configuration updated'})
    else:
        return jsonify(config)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'data': 'Connected to Solar Assistant'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_update')
def handle_request_update():
    emit('system_update', asdict(server.system_status))

if __name__ == '__main__':
    try:
        server.initialize()
        socketio.run(
            app,
            host=config['web_server']['host'],
            port=config['web_server']['port'],
            debug=config['web_server']['debug']
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)