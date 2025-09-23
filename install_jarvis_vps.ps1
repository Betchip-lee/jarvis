# PowerShell Installation Script for JARVIS AI Trading System
# Run as Administrator on Windows VPS

Write-Host "🤖 JARVIS AI Trading System - Windows VPS Installation Script" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Running as Administrator" -ForegroundColor Green

# Set execution policy
Write-Host "📋 Setting PowerShell execution policy..." -ForegroundColor Yellow
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force

# Create installation directory
$INSTALL_DIR = "C:\Trading"
$JARVIS_DIR = "$INSTALL_DIR\jarvis-ai"

Write-Host "📁 Creating installation directory: $INSTALL_DIR" -ForegroundColor Yellow
if (!(Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force
}

# Function to download and install software
function Install-Software {
    param($Name, $Url, $InstallerName, $Args = "/S")
    
    Write-Host "📥 Downloading $Name..." -ForegroundColor Yellow
    $installer = "$env:TEMP\$InstallerName"
    
    try {
        Invoke-WebRequest -Uri $Url -OutFile $installer -UseBasicParsing
        Write-Host "🔧 Installing $Name..." -ForegroundColor Yellow
        Start-Process -FilePath $installer -ArgumentList $Args -Wait
        Remove-Item $installer -Force
        Write-Host "✅ $Name installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install $Name`: $_" -ForegroundColor Red
    }
}

# Install Python 3.11
Write-Host "🐍 Installing Python 3.11..." -ForegroundColor Cyan
$pythonUrl = "https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe"
Install-Software "Python 3.11" $pythonUrl "python-installer.exe" "/quiet InstallAllUsers=1 PrependPath=1"

# Install Git
Write-Host "📋 Installing Git for Windows..." -ForegroundColor Cyan
$gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe"
Install-Software "Git" $gitUrl "git-installer.exe" "/VERYSILENT /NORESTART"

# Refresh environment variables
Write-Host "🔄 Refreshing environment variables..." -ForegroundColor Yellow
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Wait for Python installation to complete
Start-Sleep -Seconds 10

# Verify Python installation
Write-Host "🔍 Verifying Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python installed: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python installation failed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python manually from python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to continue anyway"
}

# Install MetaTrader 5
Write-Host "📊 Installing MetaTrader 5..." -ForegroundColor Cyan
$mt5Url = "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
Install-Software "MetaTrader 5" $mt5Url "mt5setup.exe" "/auto"

# Create JARVIS project directory
Write-Host "📁 Setting up JARVIS project directory..." -ForegroundColor Yellow
Set-Location $INSTALL_DIR

# Clone or setup JARVIS files (assuming files are already in workspace)
Write-Host "📋 Setting up JARVIS files..." -ForegroundColor Yellow
if (!(Test-Path $JARVIS_DIR)) {
    New-Item -ItemType Directory -Path $JARVIS_DIR -Force
}

Set-Location $JARVIS_DIR

# Create Python virtual environment
Write-Host "🐍 Creating Python virtual environment..." -ForegroundColor Yellow
try {
    python -m venv jarvis-env
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to create virtual environment: $_" -ForegroundColor Red
}

# Activate virtual environment and install packages
Write-Host "📦 Installing Python packages..." -ForegroundColor Yellow
try {
    & "$JARVIS_DIR\jarvis-env\Scripts\Activate.ps1"
    
    # Upgrade pip first
    python -m pip install --upgrade pip
    
    # Install key packages one by one to avoid conflicts
    $packages = @(
        "MetaTrader5==5.0.45",
        "Flask==2.3.3",
        "pandas==2.1.1",
        "numpy==1.24.3",
        "requests==2.31.0",
        "python-telegram-bot==20.5",
        "python-dotenv==1.0.0",
        "psutil==5.9.5",
        "colorama==0.4.6",
        "pywin32==306"
    )
    
    foreach ($package in $packages) {
        Write-Host "Installing $package..." -ForegroundColor Cyan
        python -m pip install $package
    }
    
    Write-Host "✅ Core packages installed" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to install packages: $_" -ForegroundColor Red
}

# Create basic JARVIS files if they don't exist
Write-Host "📄 Creating JARVIS configuration files..." -ForegroundColor Yellow

# Create .env template
$envTemplate = @"
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
DASHBOARD_URL=http://localhost:5000

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ENABLE_TRADE_NOTIFICATIONS=true

# Logging
LOG_LEVEL=INFO
CONSOLE_WIDTH=120
"@

$envTemplate | Out-File -FilePath "$JARVIS_DIR\.env.template" -Encoding UTF8

# Create service wrapper scripts
$serviceScript = @"
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
    while True:
        try:
            logging.info("Starting JARVIS main process...")
            process = subprocess.Popen(
                [str(ENV_PATH), str(MAIN_SCRIPT)],
                cwd=str(JARVIS_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
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
"@

$serviceScript | Out-File -FilePath "$JARVIS_DIR\jarvis_service.py" -Encoding UTF8

# Configure Windows Firewall
Write-Host "🔥 Configuring Windows Firewall..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "JARVIS Dashboard" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
    Write-Host "✅ Firewall rule added for port 5000" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Could not configure firewall: $_" -ForegroundColor Yellow
}

# Create startup script
$startupScript = @"
@echo off
cd /d "C:\Trading\jarvis-ai"
call jarvis-env\Scripts\activate.bat
python JARVIS_QAI_PRO.py
pause
"@

$startupScript | Out-File -FilePath "$JARVIS_DIR\start_jarvis.bat" -Encoding ASCII

# Create scheduled task for auto-start
Write-Host "⏰ Creating scheduled task for auto-start..." -ForegroundColor Yellow
try {
    $action = New-ScheduledTaskAction -Execute "python.exe" -Argument "jarvis_service.py" -WorkingDirectory $JARVIS_DIR
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleEnd
    
    Register-ScheduledTask -TaskName "JARVIS AI Trading" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
    Write-Host "✅ Scheduled task created" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Could not create scheduled task: $_" -ForegroundColor Yellow
}

# Set power settings for 24/7 operation
Write-Host "⚡ Configuring power settings for 24/7 operation..." -ForegroundColor Yellow
try {
    powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  # High Performance
    powercfg /change standby-timeout-ac 0  # Never sleep on AC
    powercfg /change hibernate-timeout-ac 0  # Never hibernate on AC
    powercfg /change monitor-timeout-ac 0  # Never turn off monitor on AC
    Write-Host "✅ Power settings configured for 24/7 operation" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Could not configure power settings: $_" -ForegroundColor Yellow
}

# Final instructions
Write-Host ""
Write-Host "🎉 JARVIS AI Trading System Installation Complete!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Copy your JARVIS Python files to: $JARVIS_DIR" -ForegroundColor White
Write-Host "2. Edit .env.template and rename to .env with your credentials" -ForegroundColor White
Write-Host "3. Install and configure MetaTrader 5 with your Pepperstone account" -ForegroundColor White
Write-Host "4. Create your Telegram bot and get the token" -ForegroundColor White
Write-Host "5. Test the installation by running: start_jarvis.bat" -ForegroundColor White
Write-Host ""
Write-Host "📁 Installation Directory: $JARVIS_DIR" -ForegroundColor Yellow
Write-Host "🌐 Dashboard will be available at: http://localhost:5000" -ForegroundColor Yellow
Write-Host "📊 MetaTrader 5 installed - configure with Pepperstone account" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  Important Security Notes:" -ForegroundColor Red
Write-Host "- Change default RDP port (3389) for security" -ForegroundColor White
Write-Host "- Enable Windows Firewall with appropriate rules" -ForegroundColor White
Write-Host "- Use strong passwords for all accounts" -ForegroundColor White
Write-Host "- Consider VPN access for remote management" -ForegroundColor White
Write-Host ""
Write-Host "🔧 For troubleshooting, check logs in: $JARVIS_DIR\*.log" -ForegroundColor Cyan

Read-Host "Press Enter to finish installation"