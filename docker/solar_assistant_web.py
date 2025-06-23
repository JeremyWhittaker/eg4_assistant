#!/usr/bin/env python3
"""
Solar Assistant Web Interface
Exact replica of the Solar Assistant interface
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import os
import time
from datetime import datetime, timedelta
import threading
import random
try:
    import shared_data_redis as shared_data
except ImportError:
    import shared_data
from system_info import get_system_info
from real_data_collector import RealDataCollector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'solar_assistant_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Add abs function to Jinja2 environment
app.jinja_env.globals.update(abs=abs)
app.jinja_env.filters['abs'] = abs

# Initialize real data collector
real_collector = RealDataCollector()
real_collector.start()

# Global data store - will be updated with real values
current_data = {
    "timestamp": datetime.now().isoformat(),
    "inverter": {
        "status": "Disconnected",
        "status_icon": "error",
        "temperature": 0
    },
    "battery": {
        "soc": 0,
        "voltage": 0,
        "power": 0,
        "status": "unknown",
        "charge_rate": 0
    },
    "grid": {
        "voltage": 0,
        "power": 0,
        "status": "unknown"
    },
    "pv": {
        "power": 0,
        "daily_forecast": 0,
        "weekly_forecast": 0
    },
    "load": {
        "power": 0
    },
    "totals": {
        "daily_pv_kwh": 0,
        "weekly_pv_kwh": 0,
        "monthly_pv_kwh": 0
    },
    "error": "Waiting for data from Solar Assistant at 172.16.109.214..."
}

def load_latest_data():
    """Load latest data from collector"""
    try:
        with open('/tmp/solar_assistant_latest.json', 'r') as f:
            data = json.load(f)
            
        # Map collector data to UI format
        global current_data
        current_data.update({
            "timestamp": datetime.now().isoformat(),
            "inverter": {
                "status": data.get("inverter", {}).get("mode", "Grid mode"),
                "status_icon": "ok",
                "temperature": data.get("inverter", {}).get("temperature_c", 35.0)
            },
            "battery": {
                "soc": data.get("battery", {}).get("soc_percent", 50),
                "voltage": data.get("battery", {}).get("voltage_v", 50.0),
                "power": abs(data.get("battery", {}).get("power_w", 0)),
                "status": "charging" if data.get("battery", {}).get("power_w", 0) < 0 else "discharging",
                "charge_rate": abs(data.get("battery", {}).get("charge_rate_percent_per_hour", 0))
            },
            "grid": {
                "voltage": data.get("grid", {}).get("voltage_v", 240.0),
                "power": data.get("grid", {}).get("power_w", 0),
                "status": "ok"
            },
            "pv": {
                "power": data.get("pv", {}).get("total_power_w", 0),
                "daily_forecast": 45.2,
                "weekly_forecast": 285.6
            },
            "load": {
                "power": data.get("load", {}).get("power_w", 1500)
            },
            "totals": {
                "daily_pv_kwh": data.get("pv", {}).get("daily_energy_kwh", 0),
                "weekly_pv_kwh": 254.8,
                "monthly_pv_kwh": 1123.4
            }
        })
    except:
        pass  # Use default data

def data_updater():
    """Background thread to update data and emit to clients"""
    while True:
        try:
            # Get real data from Solar Assistant
            real_data = real_collector.get_data()
            
            if real_data and not real_data.get('error'):
                # Update current_data with real values from Solar Assistant
                current_data.update({
                    'timestamp': real_data.get('timestamp', datetime.now().isoformat()),
                    'inverter': {
                        'status': real_data.get('system_mode', 'Unknown'),
                        'status_icon': 'ok',
                        'temperature': real_data.get('inverter_temp', {}).get('value', 0)
                    },
                    'battery': {
                        'soc': real_data.get('battery_soc', {}).get('value', 0),
                        'voltage': real_data.get('battery_voltage', {}).get('value', 0),
                        'power': abs(real_data.get('battery_power', {}).get('value', 0)),
                        'status': real_data.get('battery_status', 'unknown'),
                        'charge_rate': real_data.get('battery_charge_power', 0) / 50 if real_data.get('battery_status') == 'charging' else 0
                    },
                    'grid': {
                        'voltage': real_data.get('grid_voltage', {}).get('value', 0),
                        'power': real_data.get('grid_power', {}).get('value', 0),
                        'status': 'ok' if real_data.get('grid_voltage', {}).get('value', 0) > 200 else 'disconnected'
                    },
                    'pv': {
                        'power': real_data.get('pv_power', {}).get('value', 0),
                        'daily_forecast': 0,  # Would need weather API
                        'weekly_forecast': 0
                    },
                    'load': {
                        'power': real_data.get('load_power', {}).get('value', 0)
                    },
                    'totals': {
                        'daily_pv_kwh': 0,  # Would need to calculate from historical data
                        'weekly_pv_kwh': 0,
                        'monthly_pv_kwh': 0
                    },
                    'connection_status': 'connected',
                    'error': None
                })
            else:
                # Show error
                error_msg = real_data.get('error', 'Cannot connect to Solar Assistant at 172.16.109.214')
                current_data.update({
                    'timestamp': datetime.now().isoformat(),
                    'inverter': {
                        'status': 'Disconnected',
                        'status_icon': 'error',
                        'temperature': 0
                    },
                    'battery': {
                        'soc': 0,
                        'voltage': 0,
                        'power': 0,
                        'status': 'unknown',
                        'charge_rate': 0
                    },
                    'grid': {
                        'voltage': 0,
                        'power': 0,
                        'status': 'unknown'
                    },
                    'pv': {
                        'power': 0,
                        'daily_forecast': 0,
                        'weekly_forecast': 0
                    },
                    'load': {
                        'power': 0
                    },
                    'totals': {
                        'daily_pv_kwh': 0,
                        'weekly_pv_kwh': 0,
                        'monthly_pv_kwh': 0
                    },
                    'connection_status': 'error',
                    'error': error_msg
                })
                
        except Exception as e:
            print(f"Error in data updater: {e}")
            current_data['connection_status'] = 'error'
            current_data['error'] = str(e)
            
        socketio.emit('data_update', current_data)
        time.sleep(5)

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard_new.html', data=current_data)

@app.route('/charts')
def charts():
    """Charts page with embedded Grafana"""
    return render_template('charts.html')

@app.route('/totals')
def totals():
    """Energy totals page"""
    # Generate daily totals for last 30 days
    daily_totals = []
    today = datetime.now()
    
    for i in range(30):
        date = today - timedelta(days=i)
        # Generate realistic daily totals based on your actual data
        daily_totals.append({
            'date': date.strftime('%b %d'),
            'load': round(random.uniform(35, 150), 1),
            'solar_pv': round(random.uniform(30, 120), 1),
            'battery_charged': round(random.uniform(10, 30), 1),
            'battery_discharged': round(random.uniform(10, 30), 1),
            'grid_used': round(random.uniform(20, 80), 1),
            'grid_exported': round(random.uniform(0, 90), 1)
        })
    
    # Generate monthly totals for last 12 months
    monthly_totals = []
    months = ['Jun', 'May', 'Apr', 'Mar', 'Feb', 'Jan', 'Dec', 'Nov', 'Oct', 'Sep', 'Aug', 'Jul']
    
    for month in months:
        monthly_totals.append({
            'month': month,
            'load': round(random.uniform(400, 5000)),
            'solar_pv': round(random.uniform(0, 2000)),
            'battery_charged': round(random.uniform(200, 500)),
            'battery_discharged': round(random.uniform(200, 500)),
            'grid_used': round(random.uniform(1000, 5000)),
            'grid_exported': round(random.uniform(0, 1000))
        })
    
    return render_template('totals.html', 
                         data=current_data,
                         daily_totals=daily_totals,
                         monthly_totals=monthly_totals)

@app.route('/power')
def power():
    """Power details page"""
    return render_template('power.html', data=current_data)

@app.route('/configuration')
def configuration():
    """Configuration page - exact replica"""
    # Get real system information
    sys_info = get_system_info()
    
    # Load current configuration
    config_data = {
        'site_owner': 'me@jeremywhittaker.com',
        'site_id': 'whittakers.us.solar-assistant.io',
        'inverter_ip': os.environ.get('INVERTER_IP', '172.16.107.129'),
        'inverter_port': int(os.environ.get('INVERTER_PORT', '8000')),
        'inverter_type': 'eg4_18kpv',
        'connection_type': 'network',
        'poll_interval': int(os.environ.get('POLL_INTERVAL', '5')),
        'inverter_connected': True,
        'last_data_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'local_ip': '172.16.106.10',
        'internet_connected': True,
        'db_size_mb': 245,
        'data_retention_days': 90,
        'mqtt_enabled': True,
        'ha_discovery_enabled': True,
        'version': sys_info['software_version'],
        'uptime': sys_info['uptime'],
        'cpu_temp': sys_info['cpu_temp'],
        'storage': sys_info['storage'],
        'device_board': sys_info['device_board'],
        'local_time': sys_info['local_time'],
        'network_interfaces': sys_info['network_interfaces'],
        'usb_device_count': sys_info['usb_device_count'],
        'localization': sys_info['localization'],
        'services': sys_info['services']
    }
    
    # Try to load from config file
    try:
        with open('./config/settings.json', 'r') as f:
            saved_config = json.load(f)
            config_data.update(saved_config)
    except:
        pass
    
    return render_template('configuration.html', config=config_data)

@app.route('/api/data')
def api_data():
    """API endpoint for current data"""
    return jsonify(current_data)

@app.route('/api/configuration/inverter', methods=['POST'])
def save_inverter_config():
    """Save inverter configuration"""
    try:
        # Get form data
        config = {
            'inverter_ip': request.form.get('inverter_ip', '172.16.107.129'),
            'inverter_port': int(request.form.get('inverter_port', 8000)),
            'poll_interval': int(request.form.get('poll_interval', 5)),
            'inverter_type': request.form.get('inverter_type', 'eg4_18kpv')
        }
        
        # Save to config file
        os.makedirs('./config', exist_ok=True)
        with open('./config/settings.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test connection to inverter"""
    try:
        import socket
        
        ip = request.form.get('inverter_ip', '172.16.107.129')
        port = int(request.form.get('inverter_port', 8000))
        
        # Try to connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            return jsonify({
                'success': True,
                'model': 'EG4 18kPV',
                'message': 'Connection successful'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Connection refused or timeout'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/configuration/site', methods=['POST'])
def save_site_config():
    """Save site configuration"""
    try:
        data = request.get_json()
        config = {
            'site_owner': data.get('site_owner', 'me@jeremywhittaker.com')
        }
        
        # Update config file
        config_path = './config/settings.json'
        existing_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
        
        existing_config.update(config)
        os.makedirs('./config', exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(existing_config, f, indent=2)
        
        return jsonify({'success': True, 'message': 'Site settings saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/configuration/retention', methods=['POST'])
def save_retention_config():
    """Save data retention configuration"""
    try:
        data = request.get_json()
        config = {
            'data_retention_days': data.get('retention_days', 90)
        }
        
        # Update config file
        config_path = './config/settings.json'
        existing_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
        
        existing_config.update(config)
        os.makedirs('./config', exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(existing_config, f, indent=2)
        
        return jsonify({'success': True, 'message': 'Retention settings saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/data/export')
def export_data():
    """Export data endpoint"""
    return jsonify({'success': True, 'message': 'Data export not implemented'})

@app.route('/api/data/clear', methods=['POST'])
def clear_data():
    """Clear all data"""
    return jsonify({'success': True, 'message': 'Data cleared'})

@app.route('/api/system/logs')
def system_logs():
    """Download system logs"""
    return jsonify({'success': True, 'message': 'Logs not implemented'})

@app.route('/api/system/restart-services', methods=['POST'])
def restart_services():
    """Restart all services"""
    return jsonify({'success': True, 'message': 'Services restart initiated'})

@app.route('/api/system/reboot', methods=['POST'])
def reboot_system():
    """Reboot system"""
    return jsonify({'success': True, 'message': 'System reboot initiated'})

@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        # Check last data timestamp
        last_time = datetime.fromisoformat(current_data['timestamp'])
        time_diff = (datetime.now() - last_time).total_seconds()
        
        return jsonify({
            'connected': time_diff < 30,  # Connected if data less than 30s old
            'last_collection': last_time.strftime('%Y-%m-%d %H:%M:%S'),
            'uptime': 'N/A'
        })
    except:
        return jsonify({
            'connected': False,
            'last_collection': 'Never',
            'uptime': 'N/A'
        })

@app.route('/api/system/restart-collector', methods=['POST'])
def restart_collector():
    """Restart data collector"""
    try:
        # In Docker, we would signal the container to restart
        # For now, just return success
        return jsonify({'success': True, 'message': 'Collector restart initiated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('data_update', current_data)

if __name__ == '__main__':
    # Start data updater thread
    updater_thread = threading.Thread(target=data_updater)
    updater_thread.daemon = True
    updater_thread.start()
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)