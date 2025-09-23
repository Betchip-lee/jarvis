#!/usr/bin/env python3
"""
Enhanced Telegram Bot for JARVIS AI Trading System
Provides trade updates, dashboard access, and full control via Telegram
"""

import os, time, requests, sqlite3, datetime as dt
import json
from typing import Optional, Dict, List

# Import MT5 integration
try:
    from mt5_integration import get_mt5_manager, ensure_mt5_connection
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

BOT = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5000")
ENABLE_TRADE_NOTIFICATIONS = os.getenv("ENABLE_TRADE_NOTIFICATIONS", "true").lower() == "true"

def send(msg: str, parse_mode: str = None):
    """Send message to Telegram chat"""
    if not BOT or not CHAT:
        print(f"Telegram not configured: {msg}")
        return
    
    try:
        data = {'chat_id': CHAT, 'text': msg}
        if parse_mode:
            data['parse_mode'] = parse_mode
        
        response = requests.post(
            f"https://api.telegram.org/bot{BOT}/sendMessage",
            data=data,
            timeout=10
        )
        
        if not response.ok:
            print(f"Telegram send error: {response.text}")
            
    except Exception as e:
        print(f"Telegram send exception: {e}")

def get_dashboard_stats() -> Dict:
    """Get current dashboard statistics"""
    DB = os.getenv("SQLITE_DB_PATH", "jarvis_qai_pro.db")
    
    try:
        con = sqlite3.connect(DB)
        c = con.cursor()
        today = dt.date.today().isoformat()
        
        # Overall stats
        c.execute("SELECT COALESCE(SUM(profit),0), COUNT(*) FROM trade_log WHERE date=?", (today,))
        s = c.fetchone() or (0.0, 0)
        total_profit = float(s[0] or 0.0)
        total_trades = int(s[1] or 0)
        
        # Win rate
        c.execute("SELECT COUNT(*) FROM trade_log WHERE date=? AND profit>0", (today,))
        wins = int((c.fetchone() or (0,))[0])
        win_rate = wins / max(1, total_trades)
        
        # Ghost vs Live stats
        c.execute("SELECT mode, COUNT(*), SUM(profit) FROM trade_log WHERE date=? GROUP BY mode", (today,))
        mode_stats = {}
        for row in c.fetchall():
            mode = row[0] or 'LIVE'
            mode_stats[mode] = {'trades': row[1], 'profit': row[2] or 0.0}
        
        con.close()
        
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'wins': wins,
            'losses': total_trades - wins,
            'mode_stats': mode_stats
        }
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {}

def get_mt5_status() -> Dict:
    """Get MT5 connection and account status"""
    if not MT5_AVAILABLE:
        return {'connected': False, 'error': 'MT5 not available'}
    
    try:
        mt5_manager = get_mt5_manager()
        if not mt5_manager.is_connected():
            return {'connected': False, 'error': 'Not connected'}
        
        account_info = mt5_manager.get_account_info()
        positions = mt5_manager.get_positions()
        
        return {
            'connected': True,
            'account_info': account_info,
            'open_positions': len(positions),
            'positions': positions
        }
        
    except Exception as e:
        return {'connected': False, 'error': str(e)}

def format_status_message() -> str:
    """Format comprehensive status message"""
    stats = get_dashboard_stats()
    mt5_status = get_mt5_status()
    
    # Basic stats
    profit = stats.get('total_profit', 0.0)
    trades = stats.get('total_trades', 0)
    win_rate = stats.get('win_rate', 0.0) * 100
    
    message = f"🤖 *JARVIS AI Trading Status*\n\n"
    message += f"📊 *Today's Performance:*\n"
    message += f"💰 Profit: £{profit:.2f}\n"
    message += f"📈 Trades: {trades} ({stats.get('wins', 0)}W/{stats.get('losses', 0)}L)\n"
    message += f"🎯 Win Rate: {win_rate:.1f}%\n\n"
    
    # Mode breakdown
    mode_stats = stats.get('mode_stats', {})
    ghost_stats = mode_stats.get('GHOST', {})
    live_stats = mode_stats.get('LIVE', {})
    
    message += f"🔍 *Ghost Trading:*\n"
    message += f"Trades: {ghost_stats.get('trades', 0)} | Profit: £{ghost_stats.get('profit', 0.0):.2f}\n\n"
    message += f"💼 *Live Trading:*\n"
    message += f"Trades: {live_stats.get('trades', 0)} | Profit: £{live_stats.get('profit', 0.0):.2f}\n\n"
    
    # MT5 Status
    if mt5_status['connected']:
        account = mt5_status.get('account_info', {})
        message += f"🔗 *MT5 Status:* ✅ Connected\n"
        message += f"💳 Balance: £{account.get('balance', 0):.2f}\n"
        message += f"📊 Equity: £{account.get('equity', 0):.2f}\n"
        message += f"📍 Open Positions: {mt5_status.get('open_positions', 0)}\n"
    else:
        message += f"🔗 *MT5 Status:* ❌ {mt5_status.get('error', 'Disconnected')}\n"
    
    message += f"\n🌐 [Open Dashboard]({DASHBOARD_URL})"
    
    return message

def handle_command(command: str, args: List[str]) -> str:
    """Handle Telegram bot commands"""
    command = command.lower()
    
    if command == "status":
        return format_status_message()
    
    elif command == "help":
        return """🤖 *JARVIS AI Trading Bot Commands:*

📊 `/status` - Get current trading status
🛑 `/killswitch` - Emergency stop all trading
🎯 `/target <amount>` - Set daily profit target
⚙️ `/mode <sniper|normal>` - Set trading mode
📅 `/profile <weekend|weekday>` - Set trading profile
🔄 `/restart` - Restart trading engine
💰 `/balance` - Get account balance
📈 `/positions` - Show open positions
⚡ `/ghost <on|off>` - Enable/disable ghost trading
🌐 `/dashboard` - Get dashboard link
🔧 `/settings` - Show current settings

Use `/help <command>` for specific command help."""
    
    elif command == "killswitch":
        os.environ["AUTO_TRADING"] = "false"
        return "🛑 *KILLSWITCH ENGAGED* - All trading stopped!\n\nUse `/restart` to resume trading."
    
    elif command == "restart":
        os.environ["AUTO_TRADING"] = "true"
        return "🔄 *Trading restarted* - JARVIS is back online!"
    
    elif command == "target":
        if args:
            try:
                target = float(args[0])
                os.environ["DAILY_TARGET_PROFIT"] = str(target)
                return f"🎯 Daily profit target set to £{target:.2f}"
            except ValueError:
                return "❌ Invalid target amount. Use: `/target 100.50`"
        return "❌ Please specify target amount: `/target <amount>`"
    
    elif command == "mode":
        if args:
            mode = args[0].lower()
            if mode == "sniper":
                os.environ["MAX_ENTRIES_PER_HOUR"] = "30"
                return "🎯 *Sniper mode activated* - Max 30 entries/hour"
            elif mode == "normal":
                os.environ["MAX_ENTRIES_PER_HOUR"] = "60"
                return "⚡ *Normal mode activated* - Max 60 entries/hour"
            else:
                return "❌ Invalid mode. Use: `sniper` or `normal`"
        return "❌ Please specify mode: `/mode <sniper|normal>`"
    
    elif command == "balance":
        mt5_status = get_mt5_status()
        if mt5_status['connected']:
            account = mt5_status.get('account_info', {})
            balance = account.get('balance', 0)
            equity = account.get('equity', 0)
            margin = account.get('margin', 0)
            free_margin = account.get('free_margin', 0)
            
            message = f"💰 *Account Balance:*\n"
            message += f"Balance: £{balance:.2f}\n"
            message += f"Equity: £{equity:.2f}\n"
            message += f"Margin Used: £{margin:.2f}\n"
            message += f"Free Margin: £{free_margin:.2f}\n"
            
            return message
        else:
            return f"❌ MT5 not connected: {mt5_status.get('error', 'Unknown error')}"
    
    elif command == "dashboard":
        return f"🌐 *JARVIS Dashboard:*\n[Open Dashboard]({DASHBOARD_URL})\n\nFull control panel with real-time stats, trading controls, and position management."
    
    else:
        return f"❌ Unknown command: `{command}`\nUse `/help` for available commands."

def poll():
    """Main polling loop for Telegram bot"""
    if not BOT:
        print("TELEGRAM_BOT_TOKEN not set. Telegram bot disabled.")
        return
    
    print(f"Starting Telegram bot polling... Chat ID: {CHAT}")
    send("🤖 *JARVIS AI Trading Bot Online*\n\nUse `/help` for commands or `/status` for current stats.", parse_mode="Markdown")
    
    offset = None
    
    while True:
        try:
            # Get updates from Telegram
            params = {"timeout": 30, "offset": offset}
            response = requests.get(
                f"https://api.telegram.org/bot{BOT}/getUpdates",
                params=params,
                timeout=35
            )
            
            if not response.ok:
                print(f"Telegram API error: {response.text}")
                time.sleep(5)
                continue
            
            updates = response.json().get("result", [])
            
            for update in updates:
                offset = update["update_id"] + 1
                
                message = update.get("message", {})
                text = message.get("text", "").strip()
                
                if not text or not text.startswith("/"):
                    continue
                
                # Parse command and arguments
                parts = text[1:].split()
                command = parts[0] if parts else ""
                args = parts[1:] if len(parts) > 1 else []
                
                # Handle command
                try:
                    response_text = handle_command(command, args)
                    send(response_text, parse_mode="Markdown")
                except Exception as e:
                    error_msg = f"❌ Error executing command: {str(e)}"
                    send(error_msg)
                    print(f"Command error: {e}")
        
        except requests.exceptions.Timeout:
            # Timeout is expected with long polling
            continue
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    poll()