# JARVIS AI Trading System - Quick Start Guide

## 🚀 Quick Deployment to Windows VPS

### Option 1: Automated Installation (Recommended)
1. **Download PowerShell Script**: Copy `install_jarvis_vps.ps1` to your Windows VPS
2. **Run as Administrator**: Right-click PowerShell → "Run as Administrator"
3. **Execute**: `.\install_jarvis_vps.ps1`
4. **Follow prompts**: The script will install Python, MT5, Git, and configure everything

### Option 2: Manual Installation
Follow the detailed steps in `WINDOWS_VPS_DEPLOYMENT.md`

## 📋 Pre-Deployment Checklist

### Before You Start
- [ ] Windows VPS with 4GB+ RAM and stable internet
- [ ] Pepperstone MT5 account credentials ready
- [ ] Telegram bot token created (talk to @BotFather)
- [ ] Your Telegram chat ID (message @userinfobot)

### Required Credentials
Create these before deployment:
```
MT5_LOGIN=your_pepperstone_account_number
MT5_PASSWORD=your_pepperstone_password  
MT5_SERVER=PepperstoneUK-Live (or your server)
TELEGRAM_BOT_TOKEN=bot_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

## 🔧 Post-Installation Setup

### 1. Copy JARVIS Files
After running the installer, copy these files to `C:\Trading\jarvis-ai\`:
- `JARVIS_QAI_PRO.py`
- `mt5_integration.py`
- `jarvis_dash.py`
- `telegram_bot_enhanced.py`
- `templates/dashboard.html`
- All other project files

### 2. Configure Environment
1. Navigate to `C:\Trading\jarvis-ai\`
2. Rename `.env.template` to `.env`
3. Edit `.env` with your actual credentials:
```env
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=PepperstoneUK-Live
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### 3. Setup MetaTrader 5
1. Open MT5 terminal (installed by script)
2. Login with your Pepperstone credentials
3. Enable automated trading: Tools → Options → Expert Advisors → "Allow automated trading"
4. Verify symbols are loading correctly

### 4. Test Installation
1. Open PowerShell in `C:\Trading\jarvis-ai\`
2. Activate environment: `jarvis-env\Scripts\activate`
3. Test main script: `python JARVIS_QAI_PRO.py`
4. Test dashboard: `python jarvis_dash.py`
5. Test Telegram bot: `python telegram_bot_enhanced.py`

## 🌐 Access Your JARVIS System

### Dashboard Access
- **Local**: http://localhost:5000
- **Remote**: http://YOUR_VPS_IP:5000

### Telegram Commands
- `/status` - System and trading status
- `/balance` - Account balance and equity
- `/dashboard` - Get dashboard link
- `/help` - List all commands

## 🔄 24/7 Operation

The installation script automatically configures:
- **Scheduled Tasks**: Auto-start JARVIS on boot
- **Power Settings**: Never sleep/hibernate
- **Firewall Rules**: Allow dashboard access
- **Service Monitoring**: Auto-restart on crashes

## 📊 Monitoring & Health

### Real-time Monitoring
- **Dashboard**: Real-time trading stats and controls
- **Telegram**: Instant notifications and status updates
- **Logs**: Detailed logging in `C:\Trading\jarvis-ai\*.log`

### Health Checks
The system automatically monitors:
- CPU and memory usage
- Trading connection status
- Process health and auto-restart
- Daily profit/loss tracking

## 🚨 Emergency Controls

### Telegram Emergency Commands
- `/killswitch` - Stop all trading immediately
- `/restart` - Restart JARVIS system
- `/mode live` - Switch to live trading
- `/mode ghost` - Switch to ghost trading only

### Manual Control
- **Dashboard**: Use web interface for full control
- **Stop Trading**: Set `AUTO_TRADING=false` in .env
- **Emergency Stop**: Kill Python processes in Task Manager

## 🔧 Common Issues & Solutions

### Issue: "MT5 Connection Failed"
**Solution**: 
1. Verify MT5 is running and logged in
2. Check credentials in .env file
3. Ensure "Allow automated trading" is enabled

### Issue: "Dashboard not accessible"
**Solution**:
1. Check Windows Firewall settings
2. Verify port 5000 is open
3. Check if dashboard service is running

### Issue: "Telegram bot not responding"
**Solution**:
1. Verify bot token and chat ID
2. Check internet connection
3. Test bot manually with @BotFather

### Issue: "Trading not executing"
**Solution**:
1. Check `AUTO_TRADING=true` in .env
2. Verify sufficient account balance
3. Check for error messages in logs

## 📈 Optimization Tips

### Performance
- **Monitor Resources**: Keep CPU < 80%, RAM < 90%
- **Network**: Ensure stable, low-latency connection
- **Updates**: Keep Windows and MT5 updated

### Trading
- **Start Conservative**: Begin with small position sizes
- **Monitor Ghost Learning**: Let ghost traders learn patterns
- **Risk Management**: Set appropriate stop losses
- **Regular Reviews**: Analyze performance weekly

## 📞 Support & Maintenance

### Daily Tasks
- [ ] Check Telegram status messages
- [ ] Verify dashboard accessibility
- [ ] Review trading performance

### Weekly Tasks
- [ ] Review log files for errors
- [ ] Backup database and configuration
- [ ] Check system resources

### Monthly Tasks
- [ ] Analyze comprehensive trading performance
- [ ] Optimize risk management parameters
- [ ] Plan system improvements

## 🔐 Security Best Practices

### VPS Security
- Change default RDP port from 3389
- Use strong passwords (12+ characters)
- Enable Windows Firewall
- Consider VPN for remote access
- Regular Windows security updates

### Trading Security
- Never share API keys or credentials
- Monitor account regularly
- Set appropriate daily loss limits
- Keep backup of configuration files
- Use two-factor authentication where possible

## 📋 Quick Reference

### Key Files
- **Main**: `JARVIS_QAI_PRO.py` - Core trading engine
- **Dashboard**: `jarvis_dash.py` - Web interface
- **Bot**: `telegram_bot_enhanced.py` - Telegram integration
- **Config**: `.env` - All configuration settings

### Key Directories
- **Installation**: `C:\Trading\jarvis-ai\`
- **Logs**: `C:\Trading\jarvis-ai\*.log`
- **Database**: `C:\Trading\jarvis-ai\jarvis_qai_pro.db`
- **Templates**: `C:\Trading\jarvis-ai\templates\`

### Services
- **Main Task**: "JARVIS AI Trading" in Task Scheduler
- **Auto-start**: Configured to run at system startup
- **Monitoring**: Built-in health monitoring and alerts

---

🎉 **Congratulations!** Your JARVIS AI Trading System is now ready for 24/7 operation on Windows VPS with full MT5 Pepperstone integration, unified dashboard control, and Telegram management.

For detailed troubleshooting and advanced configuration, see `WINDOWS_VPS_DEPLOYMENT.md`.