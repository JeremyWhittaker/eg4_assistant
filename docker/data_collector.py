#!/usr/bin/env python3
"""
Data Collector Service
Handles scheduled data collection and aggregation tasks
"""

import os
import yaml
import logging
import time
import schedule
from datetime import datetime, timedelta
import sqlite3
import json

# Load configuration
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config/config.yaml')
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

# Setup logging
logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self):
        self.db_path = os.environ.get('DATABASE_PATH', '/data/db/solar_assistant.db')
        self.running = True
        
    def aggregate_hourly_data(self):
        """Aggregate data into hourly averages"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get data from last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            cursor.execute("""
                INSERT INTO energy_totals (inverter_id, date, pv_energy, battery_charge, 
                                         battery_discharge, grid_import, grid_export, load_energy)
                SELECT 
                    inverter_id,
                    DATE(timestamp) as date,
                    SUM(pv_power) / 12.0 as pv_energy,
                    SUM(CASE WHEN battery_power > 0 THEN battery_power ELSE 0 END) / 12.0 as battery_charge,
                    SUM(CASE WHEN battery_power < 0 THEN ABS(battery_power) ELSE 0 END) / 12.0 as battery_discharge,
                    SUM(CASE WHEN grid_power > 0 THEN grid_power ELSE 0 END) / 12.0 as grid_import,
                    SUM(CASE WHEN grid_power < 0 THEN ABS(grid_power) ELSE 0 END) / 12.0 as grid_export,
                    SUM(load_power) / 12.0 as load_energy
                FROM realtime_data
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY inverter_id, DATE(timestamp)
                ON CONFLICT(inverter_id, date) DO UPDATE SET
                    pv_energy = pv_energy + excluded.pv_energy,
                    battery_charge = battery_charge + excluded.battery_charge,
                    battery_discharge = battery_discharge + excluded.battery_discharge,
                    grid_import = grid_import + excluded.grid_import,
                    grid_export = grid_export + excluded.grid_export,
                    load_energy = load_energy + excluded.load_energy
            """, (one_hour_ago, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info("Hourly data aggregation completed")
            
        except Exception as e:
            logger.error(f"Error aggregating hourly data: {e}")
    
    def generate_daily_report(self):
        """Generate daily energy report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            yesterday = (datetime.now() - timedelta(days=1)).date()
            
            cursor.execute("""
                SELECT 
                    i.name,
                    SUM(e.pv_energy) as total_pv,
                    SUM(e.battery_charge) as total_charge,
                    SUM(e.battery_discharge) as total_discharge,
                    SUM(e.grid_import) as total_import,
                    SUM(e.grid_export) as total_export,
                    SUM(e.load_energy) as total_load
                FROM energy_totals e
                JOIN inverters i ON e.inverter_id = i.id
                WHERE e.date = ?
                GROUP BY i.name
            """, (yesterday,))
            
            results = cursor.fetchall()
            conn.close()
            
            # Generate report
            report = {
                'date': str(yesterday),
                'inverters': []
            }
            
            for row in results:
                report['inverters'].append({
                    'name': row[0],
                    'pv_energy': round(row[1], 2),
                    'battery_charge': round(row[2], 2),
                    'battery_discharge': round(row[3], 2),
                    'grid_import': round(row[4], 2),
                    'grid_export': round(row[5], 2),
                    'load_energy': round(row[6], 2)
                })
            
            # Save report
            report_path = f"/data/reports/daily_{yesterday}.json"
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Daily report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
    
    def backup_database(self):
        """Backup the database"""
        try:
            if not config['database']['backup']['enabled']:
                return
            
            backup_dir = "/data/backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{backup_dir}/solar_assistant_{timestamp}.db"
            
            # Copy database file
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backed up to: {backup_path}")
            
            # Clean old backups
            self.cleanup_old_backups(backup_dir)
            
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
    
    def cleanup_old_backups(self, backup_dir):
        """Remove old backup files"""
        try:
            retention_days = config['database']['backup']['retention']
            cutoff_time = time.time() - (retention_days * 86400)
            
            for filename in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    logger.info(f"Removed old backup: {filename}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
    
    def check_system_health(self):
        """Check system health and log status"""
        try:
            # Check database size
            db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
            logger.info(f"Database size: {db_size:.2f} MB")
            
            # Check disk space
            stat = os.statvfs('/data')
            free_space = (stat.f_bavail * stat.f_frsize) / (1024 * 1024 * 1024)  # GB
            logger.info(f"Free disk space: {free_space:.2f} GB")
            
            # Check error logs
            # Additional health checks can be added here
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
    
    def start(self):
        """Start the data collector"""
        logger.info("Starting data collector service...")
        
        # Schedule tasks
        schedule.every().hour.at(":05").do(self.aggregate_hourly_data)
        schedule.every().day.at("00:30").do(self.generate_daily_report)
        schedule.every().day.at("03:00").do(self.backup_database)
        schedule.every().hour.at(":00").do(self.check_system_health)
        
        # Run scheduler
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the data collector"""
        self.running = False

if __name__ == '__main__':
    collector = DataCollector()
    try:
        collector.start()
    except KeyboardInterrupt:
        collector.stop()