#!/usr/bin/env python3
"""
EG4-SRP Monitor - Simplified monitoring and alerting system
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/eg4_srp_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
monitor_data = {
    'eg4': {},
    'srp': {},
    'last_update': None
}

alert_config = {
    'email_enabled': False,
    'email_to': '',
    'email_from': '',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_username': '',
    'smtp_password': '',
    'thresholds': {
        'battery_low': 20,
        'battery_high': 95,
        'peak_demand': 5.0,
        'grid_import': 10000
    }
}

class EG4Monitor:
    def __init__(self):
        self.username = os.getenv('EG4_USERNAME', '')
        self.password = os.getenv('EG4_PASSWORD', '')
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
        )
        self.page = await self.browser.new_page()
        
    async def login(self):
        try:
            await self.page.goto('https://monitor.eg4electronics.com/WManage/web/login', wait_until='domcontentloaded')
            await self.page.fill('input[name="account"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            await asyncio.sleep(3)
            return 'login' not in self.page.url
        except Exception as e:
            logger.error(f"EG4 login error: {e}")
            return False
    
    async def get_data(self):
        try:
            await self.page.goto('https://monitor.eg4electronics.com/WManage/web/monitor/inverter', wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Wait for data to load
            for _ in range(10):
                soc = await self.page.evaluate("() => document.querySelector('.socText')?.textContent")
                if soc and soc != '--':
                    break
                await asyncio.sleep(1)
            
            # Extract data
            data = await self.page.evaluate("""
                () => {
                    const cleanText = (text) => {
                        if (!text || text === '--') return '0';
                        return text.trim().replace(/[^0-9.-]/g, '');
                    };
                    
                    return {
                        battery: {
                            soc: parseInt(cleanText(document.querySelector('.socText')?.textContent)) || 0,
                            power: parseInt(cleanText(document.querySelector('.batteryPowerText')?.textContent)) || 0,
                            voltage: parseFloat(cleanText(document.querySelector('.vbatText')?.textContent)) || 0
                        },
                        pv: {
                            power: parseInt(cleanText(document.querySelector('.pvPowerText')?.textContent)) || 0
                        },
                        grid: {
                            power: parseInt(cleanText(document.querySelector('.gridPowerText')?.textContent)) || 0,
                            voltage: parseFloat(cleanText(document.querySelector('.vacText')?.textContent)) || 0
                        },
                        load: {
                            power: parseInt(cleanText(document.querySelector('.consumptionPowerText')?.textContent)) || 0
                        }
                    };
                }
            """)
            
            return data
            
        except Exception as e:
            logger.error(f"EG4 data extraction error: {e}")
            return None
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

class SRPMonitor:
    def __init__(self):
        self.username = os.getenv('SRP_USERNAME', '')
        self.password = os.getenv('SRP_PASSWORD', '')
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--single-process']
        )
        self.page = await self.browser.new_page()
        
    async def login(self):
        try:
            await self.page.goto('https://myaccount.srpnet.com/power', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Check if already logged in
            if 'dashboard' in self.page.url:
                return True
                
            # Login
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)
            await self.page.press('input[name="password"]', 'Enter')
            await asyncio.sleep(5)
            
            return 'dashboard' in self.page.url or 'myaccount' in self.page.url
            
        except Exception as e:
            logger.error(f"SRP login error: {e}")
            return False
    
    async def get_peak_demand(self):
        try:
            await self.page.goto('https://myaccount.srpnet.com/power/myaccount/usage', wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Extract peak demand
            demand_data = await self.page.evaluate("""
                () => {
                    const srpRedText = document.querySelector('.srp-red-text strong');
                    let demandValue = '0';
                    
                    if (srpRedText) {
                        demandValue = srpRedText.textContent.trim();
                    }
                    
                    return {
                        demand: parseFloat(demandValue) || 0,
                        timestamp: new Date().toISOString()
                    };
                }
            """)
            
            return demand_data
            
        except Exception as e:
            logger.error(f"SRP data error: {e}")
            return {'demand': 0}
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

def send_alert_email(subject, message):
    """Send email alert"""
    if not alert_config['email_enabled']:
        return
        
    try:
        msg = MIMEMultipart()
        msg['From'] = alert_config['email_from']
        msg['To'] = alert_config['email_to']
        msg['Subject'] = f"EG4-SRP Alert: {subject}"
        
        body = f"""
        <html>
        <body>
            <h2>EG4-SRP Monitor Alert</h2>
            <p>{message}</p>
            <hr>
            <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Current Status:</p>
            <ul>
                <li>Battery SOC: {monitor_data['eg4'].get('battery', {}).get('soc', 'N/A')}%</li>
                <li>PV Power: {monitor_data['eg4'].get('pv', {}).get('power', 'N/A')}W</li>
                <li>Grid Power: {monitor_data['eg4'].get('grid', {}).get('power', 'N/A')}W</li>
                <li>Load Power: {monitor_data['eg4'].get('load', {}).get('power', 'N/A')}W</li>
                <li>SRP Peak Demand: {monitor_data['srp'].get('demand', 'N/A')}kW</li>
            </ul>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(alert_config['smtp_server'], alert_config['smtp_port'])
        server.starttls()
        server.login(alert_config['smtp_username'], alert_config['smtp_password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Alert email sent: {subject}")
        
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")

def check_thresholds():
    """Check if any thresholds are exceeded"""
    alerts = []
    
    if 'eg4' in monitor_data and monitor_data['eg4']:
        # Battery SOC alerts
        soc = monitor_data['eg4'].get('battery', {}).get('soc', 0)
        if soc <= alert_config['thresholds']['battery_low']:
            alerts.append(('Low Battery', f'Battery SOC is {soc}% (threshold: {alert_config["thresholds"]["battery_low"]}%)'))
        elif soc >= alert_config['thresholds']['battery_high']:
            alerts.append(('High Battery', f'Battery SOC is {soc}% (threshold: {alert_config["thresholds"]["battery_high"]}%)'))
        
        # Grid import alert
        grid_power = monitor_data['eg4'].get('grid', {}).get('power', 0)
        if grid_power > alert_config['thresholds']['grid_import']:
            alerts.append(('High Grid Import', f'Grid import is {grid_power}W (threshold: {alert_config["thresholds"]["grid_import"]}W)'))
    
    if 'srp' in monitor_data and monitor_data['srp']:
        # Peak demand alert
        demand = monitor_data['srp'].get('demand', 0)
        if demand > alert_config['thresholds']['peak_demand']:
            alerts.append(('High Peak Demand', f'Peak demand is {demand}kW (threshold: {alert_config["thresholds"]["peak_demand"]}kW)'))
    
    # Send alerts
    for subject, message in alerts:
        send_alert_email(subject, message)
        socketio.emit('alert', {'subject': subject, 'message': message, 'timestamp': datetime.now().isoformat()})

async def monitor_loop():
    """Main monitoring loop with automatic recovery"""
    eg4 = EG4Monitor()
    srp = SRPMonitor()
    
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            # Start browsers
            await eg4.start()
            await srp.start()
            
            # Login with retries
            eg4_logged_in = False
            for attempt in range(3):
                if await eg4.login():
                    eg4_logged_in = True
                    logger.info("EG4 login successful")
                    break
                logger.warning(f"EG4 login attempt {attempt + 1} failed")
                await asyncio.sleep(5)
            
            if not eg4_logged_in:
                logger.error("EG4 login failed after 3 attempts")
                raise Exception("EG4 login failed")
            
            srp_logged_in = False
            for attempt in range(3):
                if await srp.login():
                    srp_logged_in = True
                    logger.info("SRP login successful")
                    break
                logger.warning(f"SRP login attempt {attempt + 1} failed")
                await asyncio.sleep(5)
            
            if not srp_logged_in:
                logger.warning("SRP login failed - continuing without SRP data")
            
            # Reset retry count on successful connection
            retry_count = 0
            
            # Main monitoring loop
            consecutive_failures = 0
            while True:
                try:
                    # Get EG4 data
                    eg4_data = await eg4.get_data()
                    if eg4_data:
                        monitor_data['eg4'] = eg4_data
                        monitor_data['last_update'] = datetime.now().isoformat()
                        socketio.emit('eg4_update', eg4_data)
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.warning(f"Failed to get EG4 data (attempt {consecutive_failures})")
                    
                    # Get SRP data (less frequently)
                    if srp_logged_in and datetime.now().minute % 5 == 0:
                        srp_data = await srp.get_peak_demand()
                        if srp_data:
                            monitor_data['srp'] = srp_data
                            socketio.emit('srp_update', srp_data)
                    
                    # Check thresholds
                    check_thresholds()
                    
                    # If too many consecutive failures, restart
                    if consecutive_failures >= 5:
                        logger.error("Too many consecutive failures, restarting monitors")
                        raise Exception("Too many consecutive data fetch failures")
                    
                    # Wait 60 seconds
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    # Break inner loop to trigger reconnection
                    break
            
        except Exception as e:
            logger.error(f"Monitor connection error: {e}")
            retry_count += 1
            
            if retry_count >= max_retries:
                logger.error(f"Max retries ({max_retries}) reached. Giving up.")
                break
            
            wait_time = min(60 * retry_count, 300)  # Max 5 minute wait
            logger.info(f"Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})")
            await asyncio.sleep(wait_time)
            
        finally:
            # Always cleanup
            try:
                await eg4.close()
            except:
                pass
            try:
                await srp.close()
            except:
                pass
    
    logger.error("Monitor loop exited unexpectedly")

# Background thread
monitor_thread = None

def start_monitoring():
    """Start monitoring in background thread"""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor_loop())
    
    global monitor_thread
    monitor_thread = threading.Thread(target=run)
    monitor_thread.daemon = True
    monitor_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify(monitor_data)

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    global alert_config
    
    if request.method == 'GET':
        # Don't send passwords
        config_copy = alert_config.copy()
        config_copy['smtp_password'] = '***' if config_copy['smtp_password'] else ''
        return jsonify(config_copy)
    
    elif request.method == 'POST':
        data = request.json
        
        # Update thresholds
        if 'thresholds' in data:
            alert_config['thresholds'].update(data['thresholds'])
        
        # Update email settings
        if 'email_enabled' in data:
            alert_config['email_enabled'] = data['email_enabled']
        if 'email_to' in data:
            alert_config['email_to'] = data['email_to']
        if 'email_from' in data:
            alert_config['email_from'] = data['email_from']
        if 'smtp_server' in data:
            alert_config['smtp_server'] = data['smtp_server']
        if 'smtp_port' in data:
            alert_config['smtp_port'] = data['smtp_port']
        if 'smtp_username' in data:
            alert_config['smtp_username'] = data['smtp_username']
        if 'smtp_password' in data and data['smtp_password'] != '***':
            alert_config['smtp_password'] = data['smtp_password']
        
        return jsonify({'status': 'success'})

@app.route('/api/test-email')
def test_email():
    send_alert_email('Test Alert', 'This is a test alert from EG4-SRP Monitor')
    return jsonify({'status': 'success'})

@socketio.on('connect')
def handle_connect():
    emit('connected', {'data': 'Connected to EG4-SRP Monitor'})
    # Send current data
    if monitor_data['eg4']:
        emit('eg4_update', monitor_data['eg4'])
    if monitor_data['srp']:
        emit('srp_update', monitor_data['srp'])

if __name__ == '__main__':
    # Start monitoring on startup if credentials exist
    if os.getenv('EG4_USERNAME') and os.getenv('EG4_PASSWORD'):
        start_monitoring()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)