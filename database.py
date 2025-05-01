# database.py
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict
import time
import os

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    # Create devices table
    c.execute('''CREATE TABLE IF NOT EXISTS devices
                 (mac TEXT PRIMARY KEY,
                  name TEXT,
                  ipv4 TEXT,
                  vendor TEXT,
                  model TEXT,
                  os_version TEXT,
                  description TEXT,
                  last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create firewall_rules table
    c.execute('''CREATE TABLE IF NOT EXISTS firewall_rules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  rule_type TEXT,
                  target TEXT,
                  protocol TEXT,
                  action TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create device data rates table
    c.execute('''CREATE TABLE IF NOT EXISTS device_data_rates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  mac TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  data_rate REAL,
                  FOREIGN KEY(mac) REFERENCES devices(mac))''')
    
    # Create data rate config table
    c.execute('''CREATE TABLE IF NOT EXISTS data_rate_config
                 (id INTEGER PRIMARY KEY,
                  retention_days INTEGER DEFAULT 30)''')
    
    # Create IPS configuration table
    c.execute('''CREATE TABLE IF NOT EXISTS ips_config
                 (id INTEGER PRIMARY KEY,
                  enabled BOOLEAN DEFAULT 1,
                  throttle_minutes INTEGER DEFAULT 5,
                  notification_email TEXT,
                  notification_phone TEXT)''')
    
    # Create device thresholds table
    c.execute('''CREATE TABLE IF NOT EXISTS device_thresholds
                 (mac TEXT PRIMARY KEY,
                  max_data_rate REAL DEFAULT 100.0,
                  min_data_rate REAL DEFAULT 10.0,
                  FOREIGN KEY(mac) REFERENCES devices(mac))''')
    
    # Create IPS events table
    c.execute('''CREATE TABLE IF NOT EXISTS ips_events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  mac TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  detected_rate REAL,
                  action_taken TEXT,
                  FOREIGN KEY(mac) REFERENCES devices(mac))''')
    
    # Initialize config if not exists
    c.execute('''INSERT OR IGNORE INTO data_rate_config (id, retention_days) 
                 VALUES (1, 30)''')
    
    # Initialize IPS config if not exists
    c.execute('''INSERT OR IGNORE INTO ips_config (id, enabled, throttle_minutes) 
                 VALUES (1, 1, 5)''')
    
    conn.commit()
    conn.close()

def save_device_info(device: Dict):
    """Save or update device information in database"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''INSERT OR REPLACE INTO devices 
                 (mac, name, ipv4, vendor, model, os_version, description)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (device.get('mac'),
               device.get('name'),
               device.get('ipv4'),
               device.get('vendor'),
               device.get('model'),
               device.get('version'),
               device.get('description')))
    
    conn.commit()
    conn.close()

def record_data_rate(mac: str, data_rate: float):
    """Record a new data rate measurement for a device"""
    # Ensure we're recording in KB/s (convert from B/s if needed)
    if data_rate < 0.1:  # If rate is suspiciously low (likely in B/s)
        data_rate *= 1024  # Convert to KB/s
    
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO device_data_rates (mac, data_rate)
                 VALUES (?, ?)''', (mac, data_rate))
    
    conn.commit()
    conn.close()

def get_data_rate_history(mac: str, days: int = 7) -> List[Dict]:
    """Get data rate history for a device"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''SELECT timestamp, data_rate 
                 FROM device_data_rates 
                 WHERE mac = ? AND timestamp >= datetime('now', ?)
                 ORDER BY timestamp''', 
              (mac, f'-{days} days'))
    
    results = c.fetchall()
    conn.close()
    
    return [{'timestamp': row[0], 'data_rate': row[1]} for row in results]

def get_retention_days() -> int:
    """Get current retention period in days"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('SELECT retention_days FROM data_rate_config WHERE id = 1')
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else 30

def set_retention_days(days: int):
    """Update retention period"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('UPDATE data_rate_config SET retention_days = ? WHERE id = 1', (days,))
    conn.commit()
    conn.close()

def cleanup_old_records():
    """Delete records older than retention period"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    days = get_retention_days()
    c.execute('''DELETE FROM device_data_rates 
                 WHERE timestamp < datetime('now', ?)''', 
              (f'-{days} days',))
    
    conn.commit()
    conn.close()

def get_device_info(mac: str) -> Dict:
    """Retrieve device information from database"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''SELECT name, ipv4, vendor, model, os_version, description 
                 FROM devices WHERE mac = ?''', (mac,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'name': result[0],
            'ipv4': result[1],
            'vendor': result[2],
            'model': result[3],
            'version': result[4],
            'description': result[5]
        }
    return {}

def get_all_devices() -> List[Dict]:
    """Get all devices from database"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''SELECT mac, name, ipv4, vendor, model, os_version, description 
                 FROM devices ORDER BY last_seen DESC''')
    results = c.fetchall()
    conn.close()
    
    devices = []
    for row in results:
        devices.append({
            'mac': row[0],
            'name': row[1],
            'ipv4': row[2],
            'vendor': row[3],
            'model': row[4],
            'os_version': row[5],
            'description': row[6],
            'source': 'database'
        })
    return devices

def save_firewall_rules(rules: List[Dict]):
    """Save firewall rules to database"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    # Clear existing rules
    c.execute('DELETE FROM firewall_rules')
    
    # Insert new rules
    for rule in rules:
        c.execute('''INSERT INTO firewall_rules 
                     (rule_type, target, protocol, action)
                     VALUES (?, ?, ?, ?)''',
                  (rule.get('type'),
                   rule.get('target'),
                   rule.get('protocol'),
                   rule.get('action')))
    
    conn.commit()
    conn.close()

def load_firewall_rules() -> List[Dict]:
    """Load firewall rules from database"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''SELECT rule_type, target, protocol, action 
                 FROM firewall_rules ORDER BY created_at''')
    results = c.fetchall()
    conn.close()
    
    rules = []
    for row in results:
        rules.append({
            'type': row[0],
            'target': row[1],
            'protocol': row[2],
            'action': row[3]
        })
    return rules

def get_database_tables() -> List[Dict]:
    """Get list of all tables in database"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [{'name': row[0]} for row in c.fetchall()]
    conn.close()
    return tables

def get_table_data(table_name: str) -> List[Dict]:
    """Get all data from a specific table"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    # Get column names
    c.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in c.fetchall()]
    
    # Get table data
    c.execute(f"SELECT * FROM {table_name}")
    rows = c.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    return [dict(zip(columns, row)) for row in rows]

# IPS-related functions
def get_device_thresholds(mac: str = None) -> List[Dict]:
    """Get device threshold configurations"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    if mac:
        c.execute('''SELECT mac, max_data_rate, min_data_rate 
                     FROM device_thresholds WHERE mac = ?''', (mac,))
    else:
        c.execute('''SELECT mac, max_data_rate, min_data_rate 
                     FROM device_thresholds''')
    
    results = c.fetchall()
    conn.close()
    
    return [{
        'mac': row[0],
        'max_data_rate': row[1],
        'min_data_rate': row[2]
    } for row in results]

def set_device_thresholds(mac: str, max_rate: float, min_rate: float):
    """Set data rate thresholds for a device"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''INSERT OR REPLACE INTO device_thresholds 
                 (mac, max_data_rate, min_data_rate)
                 VALUES (?, ?, ?)''',
              (mac, max_rate, min_rate))
    
    conn.commit()
    conn.close()

def get_ips_config() -> Dict:
    """Get IPS configuration"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''SELECT enabled, throttle_minutes, notification_email, notification_phone 
                 FROM ips_config WHERE id = 1''')
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'enabled': bool(result[0]),
            'throttle_minutes': result[1],
            'notification_email': result[2],
            'notification_phone': result[3]
        }
    return {}

def update_ips_config(enabled: bool, throttle_minutes: int, 
                     email: str = None, phone: str = None):
    """Update IPS configuration"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''UPDATE ips_config 
                 SET enabled = ?, throttle_minutes = ?,
                     notification_email = ?, notification_phone = ?
                 WHERE id = 1''',
              (int(enabled), throttle_minutes, email, phone))
    
    conn.commit()
    conn.close()

def record_ips_event(mac: str, rate: float, action: str):
    """Record an IPS event"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO ips_events (mac, detected_rate, action_taken)
                 VALUES (?, ?, ?)''', (mac, rate, action))
    
    conn.commit()
    conn.close()

def get_ips_events(limit: int = 50) -> List[Dict]:
    """Get recent IPS events"""
    conn = sqlite3.connect('iot_guardian.db')
    c = conn.cursor()
    
    c.execute('''SELECT mac, timestamp, detected_rate, action_taken 
                 FROM ips_events 
                 ORDER BY timestamp DESC 
                 LIMIT ?''', (limit,))
    
    results = c.fetchall()
    conn.close()
    
    return [{
        'mac': row[0],
        'timestamp': row[1],
        'detected_rate': row[2],
        'action_taken': row[3]
    } for row in results]

# Initialize database when module is imported
init_db()