"""
Redis-based shared data module for communication between collector and web app
"""

import redis
import json
from datetime import datetime

# Redis connection
_redis_client = None

def _get_redis():
    """Get Redis connection"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
    return _redis_client

def update_data(new_data):
    """Update shared data in Redis"""
    try:
        # Add timestamp
        new_data['timestamp'] = datetime.now().isoformat()
        
        # Store in Redis
        r = _get_redis()
        r.set('solar_assistant:current_data', json.dumps(new_data))
        r.expire('solar_assistant:current_data', 60)  # Expire after 60 seconds
        
        # Also store individual keys for easy access
        for key, value in new_data.items():
            r.hset('solar_assistant:values', key, json.dumps(value))
        
        return True
    except Exception as e:
        print(f"Error updating Redis data: {e}")
        return False

def get_data():
    """Get current data from Redis"""
    try:
        r = _get_redis()
        data_json = r.get('solar_assistant:current_data')
        
        if data_json:
            return json.loads(data_json)
        else:
            # Return default data
            return {
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
                'connection_status': 'disconnected',
                'error': 'No data available'
            }
    except Exception as e:
        print(f"Error getting Redis data: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'connection_status': 'disconnected',
            'error': f'Redis error: {str(e)}'
        }