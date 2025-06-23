"""
Shared data module for communication between collector and web app
"""

import threading
from datetime import datetime

# Thread-safe shared data
_data_lock = threading.Lock()
_current_data = {
    'timestamp': datetime.now().isoformat(),
    'pv_power_total': 0,
    'pv1_power': 0,
    'pv2_power': 0,
    'pv3_power': 0,
    'battery_voltage': 52.8,
    'battery_current': 0,
    'battery_power': 0,
    'battery_soc': 75,
    'battery_temp': 25.5,
    'battery_state': 'idle',
    'grid_voltage': 240.0,
    'grid_frequency': 60.0,
    'grid_power': 0,
    'grid_state': 'standby',
    'load_power': 0,
    'inverter_temp': 45.0,
    'today_energy': 0,
}

def update_data(new_data):
    """Update shared data with thread safety"""
    global _current_data
    with _data_lock:
        _current_data.update(new_data)
        _current_data['timestamp'] = datetime.now().isoformat()

def get_data():
    """Get current data with thread safety"""
    with _data_lock:
        return _current_data.copy()