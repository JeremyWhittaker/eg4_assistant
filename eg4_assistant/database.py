#!/usr/bin/env python3
"""
Database module for EG4 Assistant
Handles data persistence using SQLite and time-series storage
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os

class Database:
    def __init__(self, db_path='eg4_assistant.db'):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        cursor = self.conn.cursor()
        
        # Inverters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inverters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                model TEXT NOT NULL,
                serial_number TEXT UNIQUE,
                ip_address TEXT,
                port INTEGER DEFAULT 8000,
                protocol TEXT DEFAULT 'iotos',
                modbus_address INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Real-time data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS realtime_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inverter_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data JSON,
                FOREIGN KEY (inverter_id) REFERENCES inverters(id)
            )
        ''')
        
        # Historical data table (aggregated)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inverter_id INTEGER,
                timestamp TIMESTAMP,
                interval TEXT, -- 'minute', 'hour', 'day', 'month'
                pv_power_avg REAL,
                pv_power_max REAL,
                battery_power_avg REAL,
                battery_soc_avg REAL,
                grid_power_avg REAL,
                load_power_avg REAL,
                energy_produced REAL,
                energy_consumed REAL,
                energy_exported REAL,
                energy_imported REAL,
                FOREIGN KEY (inverter_id) REFERENCES inverters(id)
            )
        ''')
        
        # Energy totals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_totals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inverter_id INTEGER,
                date DATE,
                energy_produced REAL DEFAULT 0,
                energy_consumed REAL DEFAULT 0,
                energy_exported REAL DEFAULT 0,
                energy_imported REAL DEFAULT 0,
                self_consumption REAL DEFAULT 0,
                peak_power REAL DEFAULT 0,
                runtime_hours REAL DEFAULT 0,
                FOREIGN KEY (inverter_id) REFERENCES inverters(id),
                UNIQUE(inverter_id, date)
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value JSON,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inverter_id INTEGER,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (inverter_id) REFERENCES inverters(id)
            )
        ''')
        
        self.conn.commit()
    
    def add_inverter(self, name: str, model: str, ip_address: str, 
                     port: int = 8000, protocol: str = 'iotos', 
                     serial_number: str = None) -> int:
        """Add a new inverter"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO inverters (name, model, ip_address, port, protocol, serial_number)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, model, ip_address, port, protocol, serial_number))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_inverters(self) -> List[Dict]:
        """Get all inverters"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM inverters')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_inverter(self, inverter_id: int) -> Dict:
        """Get specific inverter"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM inverters WHERE id = ?', (inverter_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_inverter(self, inverter_id: int, **kwargs):
        """Update inverter settings"""
        allowed_fields = ['name', 'model', 'ip_address', 'port', 'protocol', 'serial_number', 'modbus_address']
        fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if fields_to_update:
            set_clause = ', '.join([f"{k} = ?" for k in fields_to_update.keys()])
            values = list(fields_to_update.values()) + [inverter_id]
            
            cursor = self.conn.cursor()
            cursor.execute(f'''
                UPDATE inverters 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', values)
            self.conn.commit()
    
    def save_realtime_data(self, inverter_id: int, data: Dict):
        """Save real-time data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO realtime_data (inverter_id, data)
            VALUES (?, ?)
        ''', (inverter_id, json.dumps(data)))
        self.conn.commit()
        
        # Update energy totals
        self._update_energy_totals(inverter_id, data)
    
    def _update_energy_totals(self, inverter_id: int, data: Dict):
        """Update energy totals for today"""
        today = datetime.now().date()
        
        # Calculate energy (simplified - in production would be more accurate)
        energy_produced = data.get('pv_power', 0) / 60000  # kWh (assuming minute updates)
        energy_consumed = data.get('load_power', 0) / 60000
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO energy_totals (inverter_id, date, energy_produced, energy_consumed, peak_power)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(inverter_id, date) DO UPDATE SET
                energy_produced = energy_produced + ?,
                energy_consumed = energy_consumed + ?,
                peak_power = MAX(peak_power, ?)
        ''', (inverter_id, today, energy_produced, energy_consumed, data.get('pv_power', 0),
              energy_produced, energy_consumed, data.get('pv_power', 0)))
        self.conn.commit()
    
    def get_realtime_data(self, inverter_id: int, limit: int = 100) -> List[Dict]:
        """Get recent real-time data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT timestamp, data 
            FROM realtime_data 
            WHERE inverter_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (inverter_id, limit))
        
        results = []
        for row in cursor.fetchall():
            data = json.loads(row['data'])
            data['timestamp'] = row['timestamp']
            results.append(data)
        
        return results
    
    def get_energy_totals(self, inverter_id: int, period: str = 'today') -> Dict:
        """Get energy totals for a period"""
        cursor = self.conn.cursor()
        
        if period == 'today':
            cursor.execute('''
                SELECT * FROM energy_totals 
                WHERE inverter_id = ? AND date = DATE('now')
            ''', (inverter_id,))
        elif period == 'yesterday':
            cursor.execute('''
                SELECT * FROM energy_totals 
                WHERE inverter_id = ? AND date = DATE('now', '-1 day')
            ''', (inverter_id,))
        elif period == 'month':
            cursor.execute('''
                SELECT 
                    SUM(energy_produced) as energy_produced,
                    SUM(energy_consumed) as energy_consumed,
                    SUM(energy_exported) as energy_exported,
                    SUM(energy_imported) as energy_imported,
                    MAX(peak_power) as peak_power
                FROM energy_totals 
                WHERE inverter_id = ? 
                AND date >= DATE('now', 'start of month')
            ''', (inverter_id,))
        elif period == 'year':
            cursor.execute('''
                SELECT 
                    SUM(energy_produced) as energy_produced,
                    SUM(energy_consumed) as energy_consumed,
                    SUM(energy_exported) as energy_exported,
                    SUM(energy_imported) as energy_imported,
                    MAX(peak_power) as peak_power
                FROM energy_totals 
                WHERE inverter_id = ? 
                AND date >= DATE('now', 'start of year')
            ''', (inverter_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def get_historical_data(self, inverter_id: int, start_date: str, end_date: str, 
                          interval: str = 'hour') -> List[Dict]:
        """Get historical data for charting"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM historical_data
            WHERE inverter_id = ? 
            AND timestamp BETWEEN ? AND ?
            AND interval = ?
            ORDER BY timestamp
        ''', (inverter_id, start_date, end_date, interval))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def save_setting(self, key: str, value: Any):
        """Save a setting"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value) 
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET 
                value = ?, 
                updated_at = CURRENT_TIMESTAMP
        ''', (key, json.dumps(value), json.dumps(value)))
        self.conn.commit()
    
    def get_setting(self, key: str, default=None):
        """Get a setting"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row['value'])
        return default
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()