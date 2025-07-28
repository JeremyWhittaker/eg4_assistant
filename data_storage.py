#!/usr/bin/env python3
"""
Data Storage Module for EG4-SRP Monitor
Provides SQLite-based persistent storage for time-series monitoring data
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)

class DataStorage:
    """SQLite-based data storage for monitoring data"""
    
    def __init__(self, db_path: str = './data/monitor.db'):
        self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"Created data directory: {data_dir}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # SQLite optimizations for time-series data
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = 10000")
        conn.execute("PRAGMA temp_store = memory")
        
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        try:
            with self.get_connection() as conn:
                # EG4 inverter data (high frequency - every 60 seconds)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS eg4_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        battery_soc REAL,
                        battery_power REAL,
                        battery_voltage REAL,
                        pv_power REAL,
                        pv1_power REAL,
                        pv1_voltage REAL,
                        pv2_power REAL,
                        pv2_voltage REAL,
                        pv3_power REAL,
                        pv3_voltage REAL,
                        grid_power REAL,
                        grid_voltage REAL,
                        load_power REAL,
                        connection_valid BOOLEAN DEFAULT 1,
                        raw_data TEXT,  -- JSON string of full data
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # SRP utility data (daily updates)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS srp_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        chart_type TEXT NOT NULL,
                        peak_demand REAL,
                        total_usage REAL,
                        total_generation REAL,
                        net_energy REAL,
                        raw_csv_path TEXT,
                        raw_data TEXT,  -- JSON string of full data
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date, chart_type)
                    )
                ''')
                
                # System events and alerts
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        event_type TEXT NOT NULL,  -- 'alert', 'error', 'info', 'warning'
                        category TEXT NOT NULL,    -- 'battery', 'grid', 'srp', 'system'
                        message TEXT NOT NULL,
                        data TEXT,  -- JSON string for structured data
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_eg4_timestamp ON eg4_data(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_srp_date_type ON srp_data(date, chart_type)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_events_type ON system_events(event_type, category)')
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def store_eg4_data(self, data: Dict) -> bool:
        """Store EG4 data with automatic retry on connection issues"""
        try:
            with self.get_connection() as conn:
                battery = data.get('battery', {})
                pv = data.get('pv', {})
                grid = data.get('grid', {})
                load = data.get('load', {})
                
                # Extract PV string data
                pv_strings = pv.get('strings', {})
                pv1 = pv_strings.get('pv1', {})
                pv2 = pv_strings.get('pv2', {})
                pv3 = pv_strings.get('pv3', {})
                
                conn.execute('''
                    INSERT INTO eg4_data (
                        timestamp, battery_soc, battery_power, battery_voltage,
                        pv_power, pv1_power, pv1_voltage, pv2_power, pv2_voltage,
                        pv3_power, pv3_voltage, grid_power, grid_voltage, 
                        load_power, connection_valid, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now(),
                    battery.get('soc'),
                    battery.get('power'),
                    battery.get('voltage'),
                    pv.get('power'),
                    pv1.get('power'),
                    pv1.get('voltage'),
                    pv2.get('power'),
                    pv2.get('voltage'),
                    pv3.get('power'),
                    pv3.get('voltage'),
                    grid.get('power'),
                    grid.get('voltage'),
                    load.get('power'),
                    data.get('connection_valid', True),
                    json.dumps(data)
                ))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store EG4 data: {e}")
            return False
    
    def store_srp_data(self, date: str, chart_type: str, data: Dict, csv_path: str = None) -> bool:
        """Store SRP data with upsert behavior"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO srp_data (
                        date, chart_type, peak_demand, raw_csv_path, raw_data
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    date,
                    chart_type,
                    data.get('demand'),
                    csv_path,
                    json.dumps(data)
                ))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store SRP data: {e}")
            return False
    
    def store_system_event(self, event_type: str, category: str, message: str, data: Dict = None) -> bool:
        """Store system event/alert"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO system_events (
                        timestamp, event_type, category, message, data
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    datetime.now(),
                    event_type,
                    category,
                    message,
                    json.dumps(data) if data else None
                ))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store system event: {e}")
            return False
    
    def get_latest_eg4_data(self) -> Optional[Dict]:
        """Get the most recent EG4 data point"""
        try:
            with self.get_connection() as conn:
                row = conn.execute('''
                    SELECT * FROM eg4_data 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''').fetchone()
                
                if row:
                    data = dict(row)
                    # Parse raw_data if available
                    if data.get('raw_data'):
                        try:
                            data['parsed_data'] = json.loads(data['raw_data'])
                        except:
                            pass
                    return data
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve latest EG4 data: {e}")
            return None
    
    def get_latest_srp_data(self) -> Optional[Dict]:
        """Get the most recent SRP data"""
        try:
            with self.get_connection() as conn:
                row = conn.execute('''
                    SELECT * FROM srp_data 
                    ORDER BY date DESC 
                    LIMIT 1
                ''').fetchone()
                
                if row:
                    data = dict(row)
                    if data.get('raw_data'):
                        try:
                            data['parsed_data'] = json.loads(data['raw_data'])
                        except:
                            pass
                    return data
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve latest SRP data: {e}")
            return None
    
    def get_historical_eg4_data(self, hours: int = 24) -> List[Dict]:
        """Get historical EG4 data for charts and analysis"""
        try:
            with self.get_connection() as conn:
                cutoff = datetime.now() - timedelta(hours=hours)
                rows = conn.execute('''
                    SELECT * FROM eg4_data 
                    WHERE timestamp > ? 
                    ORDER BY timestamp
                ''', (cutoff,)).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to retrieve historical EG4 data: {e}")
            return []
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent system alerts"""
        try:
            with self.get_connection() as conn:
                cutoff = datetime.now() - timedelta(hours=hours)
                rows = conn.execute('''
                    SELECT * FROM system_events 
                    WHERE timestamp > ? AND event_type = 'alert'
                    ORDER BY timestamp DESC
                ''', (cutoff,)).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to retrieve recent alerts: {e}")
            return []
    
    def cleanup_old_data(self):
        """Remove old data based on retention policies"""
        try:
            with self.get_connection() as conn:
                now = datetime.now()
                
                # EG4 data: keep 90 days of raw data
                eg4_cutoff = now - timedelta(days=90)
                result = conn.execute('''
                    DELETE FROM eg4_data 
                    WHERE timestamp < ?
                ''', (eg4_cutoff,))
                
                if result.rowcount > 0:
                    logger.info(f"Cleaned up {result.rowcount} old EG4 records")
                
                # System events: keep 1 year of alerts, 6 months of errors, 30 days of info
                alert_cutoff = now - timedelta(days=365)
                error_cutoff = now - timedelta(days=180)
                info_cutoff = now - timedelta(days=30)
                
                # Clean old alerts
                result = conn.execute('''
                    DELETE FROM system_events 
                    WHERE event_type = 'alert' AND timestamp < ?
                ''', (alert_cutoff,))
                
                # Clean old errors
                result = conn.execute('''
                    DELETE FROM system_events 
                    WHERE event_type = 'error' AND timestamp < ?
                ''', (error_cutoff,))
                
                # Clean old info events
                result = conn.execute('''
                    DELETE FROM system_events 
                    WHERE event_type = 'info' AND timestamp < ?
                ''', (info_cutoff,))
                
                conn.commit()
                logger.info("Database cleanup completed")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Count records in each table
                for table in ['eg4_data', 'srp_data', 'system_events']:
                    count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                    stats[f'{table}_count'] = count
                
                # Get database file size
                if os.path.exists(self.db_path):
                    stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
                
                # Get date range for EG4 data
                eg4_range = conn.execute('''
                    SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest 
                    FROM eg4_data
                ''').fetchone()
                
                if eg4_range['earliest']:
                    stats['eg4_data_range'] = {
                        'earliest': eg4_range['earliest'],
                        'latest': eg4_range['latest']
                    }
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

class CachedDataStorage:
    """Wrapper around DataStorage with intelligent caching for dashboard performance"""
    
    def __init__(self, storage: DataStorage):
        self.storage = storage
        self.cache = {}
        self.cache_ttl = {}
    
    def get_dashboard_data(self) -> Dict:
        """Get dashboard data with intelligent caching"""
        now = datetime.now()
        cache_key = 'dashboard_data'
        
        # Check if cache is still valid (30 seconds for real-time data)
        if (cache_key in self.cache and 
            cache_key in self.cache_ttl and
            now < self.cache_ttl[cache_key]):
            return self.cache[cache_key]
        
        # Fetch fresh data
        data = {
            'latest_eg4': self.storage.get_latest_eg4_data(),
            'latest_srp': self.storage.get_latest_srp_data(),
            'recent_alerts': self.storage.get_recent_alerts(hours=24),
            'stats': self.storage.get_database_stats()
        }
        
        # Cache for 30 seconds
        self.cache[cache_key] = data
        self.cache_ttl[cache_key] = now + timedelta(seconds=30)
        
        return data
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        self.cache_ttl.clear()