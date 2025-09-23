# JARVIS AI Trading System - Windows VPS Deployment Guide

## Overview
This guide provides complete instructions for deploying the JARVIS AI trading system on a Windows VPS for 24/7 operation with MT5 and Pepperstone broker integration.

## Prerequisites

### 1. Windows VPS Requirements
- **OS**: Windows Server 2019/2022 or Windows 10/11 Pro
- **RAM**: Minimum 4GB (8GB recommended)
- **CPU**: 2+ cores
- **Storage**: 50GB+ SSD
- **Network**: Stable internet connection with low latency to broker servers
- **Remote Desktop**: Enabled for management

### 2. Required Software
- Python 3.9+ (64-bit)
- MetaTrader 5 Terminal
- Git for Windows
- Chrome/Firefox browser

## Installation Steps

### Step 1: Setup Python Environment
```cmd
# Download and install Python 3.11 from python.org
# During installation, check "Add Python to PATH"

# Verify installation
python --version
pip --version

# Install virtual environment
pip install virtualenv
```

### Step 2: Clone JARVIS Repository
```cmd
# Navigate to desired directory (e.g., C:\Trading)
cd C:\
mkdir Trading
cd Trading

# Clone your JARVIS repository
git clone <your-repo-url> jarvis-ai
cd jarvis-ai

# Create virtual environment
python -m venv jarvis-env

# Activate environment
jarvis-env\Scripts\activate

# Install dependencies
pip install -r requirements_kitchen_sink.txt
```

### Step 3: Install and Configure MT5
1. Download MetaTrader 5 from Pepperstone website
2. Install MT5 terminal
3. Login with your Pepperstone account credentials
4. Enable automated trading (Tools → Options → Expert Advisors → Allow automated trading)
5. Test connection and verify symbols are available

### Step 4: Configure Environment Variables
Create `.env` file in the JARVIS directory:

```env
# MT5 Configuration
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=PepperstoneUK-Live

# Database
SQLITE_DB_PATH=C:\Trading\jarvis-ai\jarvis_qai_pro.db

# Trading Settings
AUTO_TRADING=true
MAX_ENTRIES_PER_HOUR=60
DAILY_LOSS_STOP=100.00
WEEKEND_PROFILE_ON=1
ENABLE_GHOST=1
GHOST_RATIO=3.0

# Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000
DASHBOARD_URL=http://your-vps-ip:5000

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ENABLE_TRADE_NOTIFICATIONS=true

# Logging
LOG_LEVEL=INFO
CONSOLE_WIDTH=120
```

### Step 5: Create Windows Services

#### JARVIS Main Service Script
Create `jarvis_service.py`:

```python
import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# Setup paths
JARVIS_DIR = Path(__file__).parent
ENV_PATH = JARVIS_DIR / "jarvis-env" / "Scripts" / "python.exe"
MAIN_SCRIPT = JARVIS_DIR / "JARVIS_QAI_PRO.py"

# Setup logging
logging.basicConfig(
    filename=JARVIS_DIR / "jarvis_service.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_jarvis():
    """Run the main JARVIS trading script"""
    while True:
        try:
            logging.info("Starting JARVIS main process...")
            
            # Run JARVIS with virtual environment Python
            process = subprocess.Popen(
                [str(ENV_PATH), str(MAIN_SCRIPT)],
                cwd=str(JARVIS_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor process
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logging.error(f"JARVIS crashed with code {process.returncode}")
                logging.error(f"STDERR: {stderr}")
            
            logging.info("JARVIS process ended. Restarting in 10 seconds...")
            time.sleep(10)
            
        except Exception as e:
            logging.error(f"Error running JARVIS: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_jarvis()
```

#### Dashboard Service Script
Create `dashboard_service.py`:

```python
import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# Setup paths
JARVIS_DIR = Path(__file__).parent
ENV_PATH = JARVIS_DIR / "jarvis-env" / "Scripts" / "python.exe"
DASHBOARD_SCRIPT = JARVIS_DIR / "jarvis_dash.py"

# Setup logging
logging.basicConfig(
    filename=JARVIS_DIR / "dashboard_service.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_dashboard():
    """Run the JARVIS dashboard"""
    while True:
        try:
            logging.info("Starting JARVIS dashboard...")
            
            process = subprocess.Popen(
                [str(ENV_PATH), str(DASHBOARD_SCRIPT)],
                cwd=str(JARVIS_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logging.error(f"Dashboard crashed with code {process.returncode}")
                logging.error(f"STDERR: {stderr}")
            
            logging.info("Dashboard process ended. Restarting in 10 seconds...")
            time.sleep(10)
            
        except Exception as e:
            logging.error(f"Error running dashboard: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_dashboard()
```

#### Telegram Bot Service Script
Create `telegram_service.py`:

```python
import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# Setup paths
JARVIS_DIR = Path(__file__).parent
ENV_PATH = JARVIS_DIR / "jarvis-env" / "Scripts" / "python.exe"
TELEGRAM_SCRIPT = JARVIS_DIR / "telegram_bot_enhanced.py"

# Setup logging
logging.basicConfig(
    filename=JARVIS_DIR / "telegram_service.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_telegram_bot():
    """Run the Telegram bot"""
    while True:
        try:
            logging.info("Starting Telegram bot...")
            
            process = subprocess.Popen(
                [str(ENV_PATH), str(TELEGRAM_SCRIPT)],
                cwd=str(JARVIS_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logging.error(f"Telegram bot crashed with code {process.returncode}")
                logging.error(f"STDERR: {stderr}")
            
            logging.info("Telegram bot process ended. Restarting in 10 seconds...")
            time.sleep(10)
            
        except Exception as e:
            logging.error(f"Error running Telegram bot: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_telegram_bot()
```

### Step 6: Setup Windows Task Scheduler

#### Create JARVIS Main Task
1. Open Task Scheduler (taskschd.msc)
2. Create Basic Task
3. Name: "JARVIS AI Trading"
4. Trigger: "When the computer starts"
5. Action: "Start a program"
6. Program: `C:\Trading\jarvis-ai\jarvis-env\Scripts\python.exe`
7. Arguments: `jarvis_service.py`
8. Start in: `C:\Trading\jarvis-ai`
9. Properties → General → Run whether user is logged on or not
10. Properties → General → Run with highest privileges

#### Create Dashboard Task
Repeat above steps with:
- Name: "JARVIS Dashboard"
- Program: Same Python path
- Arguments: `dashboard_service.py`

#### Create Telegram Bot Task
Repeat above steps with:
- Name: "JARVIS Telegram Bot"
- Program: Same Python path
- Arguments: `telegram_service.py`

### Step 7: Firewall Configuration
```cmd
# Open ports for dashboard access
netsh advfirewall firewall add rule name="JARVIS Dashboard" dir=in action=allow protocol=TCP localport=5000

# Optional: Open MT5 ports (check with Pepperstone)
netsh advfirewall firewall add rule name="MT5 Trading" dir=in action=allow protocol=TCP localport=443
```

### Step 8: Setup Monitoring and Alerts

#### System Health Monitor Script
Create `health_monitor.py`:

```python
import psutil
import time
import requests
import os
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_alert(message):
    """Send alert via Telegram"""
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={'chat_id': TELEGRAM_CHAT_ID, 'text': f"🚨 VPS Alert: {message}"},
                timeout=10
            )
        except:
            pass

def monitor_system():
    """Monitor system health"""
    while True:
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                send_alert(f"High CPU usage: {cpu_percent}%")
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                send_alert(f"High memory usage: {memory.percent}%")
            
            # Check disk space
            disk = psutil.disk_usage('C:')
            if disk.percent > 90:
                send_alert(f"Low disk space: {disk.percent}% used")
            
            # Check if JARVIS processes are running
            processes = [p.name() for p in psutil.process_iter(['name'])]
            
            if 'python.exe' not in processes:
                send_alert("JARVIS processes not detected!")
            
            time.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_system()
```

## Deployment Checklist

### Pre-Deployment
- [ ] VPS provisioned with Windows Server
- [ ] Remote Desktop access configured
- [ ] Pepperstone MT5 account ready
- [ ] Telegram bot created and configured
- [ ] Domain/IP for dashboard access (optional)

### Installation
- [ ] Python 3.11 installed
- [ ] Git installed and repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] MT5 terminal installed and configured
- [ ] Environment variables configured
- [ ] Service scripts created

### Service Setup
- [ ] Task Scheduler tasks created
- [ ] All tasks set to run at startup
- [ ] Tasks configured to run with highest privileges
- [ ] Firewall rules configured
- [ ] Health monitoring enabled

### Testing
- [ ] All services start correctly
- [ ] Dashboard accessible via browser
- [ ] Telegram bot responds to commands
- [ ] MT5 connection established
- [ ] Test trades execute successfully
- [ ] Logs are being generated

### Production
- [ ] Auto-trading enabled
- [ ] Monitoring alerts configured
- [ ] Backup procedures in place
- [ ] Documentation updated
- [ ] Access credentials secured

## Maintenance

### Daily Tasks
- Check Telegram status messages
- Verify dashboard is accessible
- Review trading performance
- Monitor system resources

### Weekly Tasks
- Review log files for errors
- Update trading parameters if needed
- Backup database and configuration
- Check for software updates

### Monthly Tasks
- Analyze trading performance
- Optimize ghost trader settings
- Review risk management parameters
- Plan system improvements

## Troubleshooting

### Common Issues

#### MT5 Connection Failed
1. Verify account credentials
2. Check MT5 terminal is running
3. Ensure automated trading is enabled
4. Verify server settings

#### Dashboard Not Accessible
1. Check if service is running
2. Verify firewall settings
3. Check port 5000 is not blocked
4. Review dashboard service logs

#### Telegram Bot Not Responding
1. Verify bot token and chat ID
2. Check internet connectivity
3. Review telegram service logs
4. Test bot manually

#### Trading Not Working
1. Check AUTO_TRADING environment variable
2. Verify account has sufficient balance
3. Check for error messages in logs
4. Ensure ghost trading is configured

### Log Locations
- Main JARVIS: `jarvis_service.log`
- Dashboard: `dashboard_service.log`
- Telegram: `telegram_service.log`
- Health Monitor: Windows Event Viewer

## Security Considerations

### Network Security
- Use VPN for remote access
- Change default RDP port
- Enable Windows Firewall
- Regular security updates

### Application Security
- Secure API keys in environment variables
- Regular password changes
- Monitor access logs
- Backup encryption

### Trading Security
- Set appropriate stop losses
- Monitor position sizes
- Regular balance checks
- Emergency stop procedures

## Performance Optimization

### System Optimization
- Disable unnecessary Windows services
- Configure power settings to "High Performance"
- Regular disk cleanup
- Monitor resource usage

### Trading Optimization
- Optimize ghost trader parameters
- Adjust risk management settings
- Monitor symbol performance
- Regular strategy review

This deployment guide ensures your JARVIS AI trading system runs reliably 24/7 on Windows VPS with full MT5 Pepperstone integration.