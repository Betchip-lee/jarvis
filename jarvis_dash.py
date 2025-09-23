#!/usr/bin/env python3
"""
JARVIS AI Trading Dashboard - Single Unified Control Center
Full control dashboard for Ghost and Live MT5 trading with Pepperstone
"""

from flask import Flask, jsonify, render_template, request, redirect, url_for
import os, sqlite3, datetime as dt, json
from typing import Dict, List, Optional

# Import MT5 integration
try:
    from mt5_integration import get_mt5_manager, ensure_mt5_connection
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

app = Flask(__name__)

class DashboardData:
    """Centralized data management for the dashboard"""
    
    def __init__(self):
        self.db_path = os.getenv("SQLITE_DB_PATH", "jarvis_qai_pro.db")
        self.mt5_manager = None
        if MT5_AVAILABLE:
            self.mt5_manager = get_mt5_manager()
    
    def get_daily_stats(self) -> Dict:
        """Get comprehensive daily trading statistics"""
        con = sqlite3.connect(self.db_path)
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
        c.execute("SELECT mode, COUNT(*), SUM(profit), AVG(profit) FROM trade_log WHERE date=? GROUP BY mode", (today,))
        mode_stats = {}
        for row in c.fetchall():
            mode = row[0] or 'LIVE'
            mode_stats[mode] = {
                'trades': row[1],
                'total_profit': row[2] or 0.0,
                'avg_profit': row[3] or 0.0
            }
        
        # Hourly breakdown
        c.execute("""SELECT strftime('%H', datetime(ts, 'unixepoch')) as hour, 
                           COUNT(*), SUM(profit) 
                    FROM trade_log WHERE date=? 
                    GROUP BY hour ORDER BY hour""", (today,))
        hourly_data = {f"{row[0]}:00": {'trades': row[1], 'profit': row[2] or 0.0} for row in c.fetchall()}
        
        # Symbol performance
        c.execute("""SELECT symbol, COUNT(*), SUM(profit), AVG(profit) 
                    FROM trade_log WHERE date=? 
                    GROUP BY symbol ORDER BY SUM(profit) DESC LIMIT 10""", (today,))
        symbol_stats = []
        for row in c.fetchall():
            symbol_stats.append({
                'symbol': row[0],
                'trades': row[1], 
                'total_profit': row[2] or 0.0,
                'avg_profit': row[3] or 0.0
            })
        
        con.close()
        
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'wins': wins,
            'losses': total_trades - wins,
            'win_rate': win_rate,
            'mode_stats': mode_stats,
            'hourly_data': hourly_data,
            'symbol_stats': symbol_stats
        }
    
    def get_mt5_account_info(self) -> Optional[Dict]:
        """Get live MT5 account information"""
        if not MT5_AVAILABLE or not self.mt5_manager or not self.mt5_manager.is_connected():
            return None
        return self.mt5_manager.get_account_info()
    
    def get_mt5_positions(self) -> List[Dict]:
        """Get current MT5 positions"""
        if not MT5_AVAILABLE or not self.mt5_manager or not self.mt5_manager.is_connected():
            return []
        return self.mt5_manager.get_positions()
    
    def get_trading_settings(self) -> Dict:
        """Get current trading settings from environment"""
        return {
            'auto_trading': os.getenv("AUTO_TRADING", "true"),
            'max_entries_per_hour': os.getenv("MAX_ENTRIES_PER_HOUR", "60"),
            'daily_loss_stop': os.getenv("DAILY_LOSS_STOP", "0"),
            'weekend_profile_on': os.getenv("WEEKEND_PROFILE_ON", "1"),
            'enable_ghost': os.getenv("ENABLE_GHOST", "1"),
            'ghost_ratio': os.getenv("GHOST_RATIO", "3.0"),
            'mt5_server': os.getenv("MT5_SERVER", "PepperstoneUK-Live")
        }
    
    def update_trading_settings(self, settings: Dict) -> bool:
        """Update trading settings"""
        try:
            for key, value in settings.items():
                env_key = key.upper()
                os.environ[env_key] = str(value)
            return True
        except Exception:
            return False

dashboard_data = DashboardData()

@app.route("/")
def home():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route("/api/stats")
def api_stats():
    """API endpoint for dashboard statistics"""
    daily_stats = dashboard_data.get_daily_stats()
    account_info = dashboard_data.get_mt5_account_info()
    positions = dashboard_data.get_mt5_positions()
    settings = dashboard_data.get_trading_settings()
    
    return jsonify({
        'daily_stats': daily_stats,
        'account_info': account_info,
        'positions': positions,
        'settings': settings,
        'mt5_connected': MT5_AVAILABLE and dashboard_data.mt5_manager and dashboard_data.mt5_manager.is_connected(),
        'timestamp': dt.datetime.now().isoformat()
    })

@app.route("/api/settings", methods=['POST'])
def api_update_settings():
    """API endpoint to update trading settings"""
    try:
        settings = request.get_json()
        success = dashboard_data.update_trading_settings(settings)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/trade", methods=['POST'])
def api_manual_trade():
    """API endpoint for manual trading"""
    if not MT5_AVAILABLE or not dashboard_data.mt5_manager or not dashboard_data.mt5_manager.is_connected():
        return jsonify({'success': False, 'error': 'MT5 not connected'})
    
    try:
        trade_data = request.get_json()
        symbol = trade_data.get('symbol', '')
        action = trade_data.get('action', '')  # 'buy' or 'sell'
        volume = float(trade_data.get('volume', 0.01))
        
        if not symbol or not action:
            return jsonify({'success': False, 'error': 'Missing symbol or action'})
        
        result = dashboard_data.mt5_manager.place_order(symbol, action, volume)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/close_position", methods=['POST'])
def api_close_position():
    """API endpoint to close a position"""
    if not MT5_AVAILABLE or not dashboard_data.mt5_manager or not dashboard_data.mt5_manager.is_connected():
        return jsonify({'success': False, 'error': 'MT5 not connected'})
    
    try:
        data = request.get_json()
        ticket = int(data.get('ticket', 0))
        
        if not ticket:
            return jsonify({'success': False, 'error': 'Missing ticket'})
        
        result = dashboard_data.mt5_manager.close_position(ticket)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    daily_stats = dashboard_data.get_daily_stats()
    
    metrics_text = f"""# HELP jarvis_today_realized Today's realized profit
# TYPE jarvis_today_realized gauge
jarvis_today_realized {daily_stats['total_profit']}

# HELP jarvis_today_trades Today's total trades
# TYPE jarvis_today_trades counter
jarvis_today_trades {daily_stats['total_trades']}

# HELP jarvis_today_winrate Today's win rate
# TYPE jarvis_today_winrate gauge
jarvis_today_winrate {daily_stats['win_rate']}

# HELP jarvis_mt5_connected MT5 connection status
# TYPE jarvis_mt5_connected gauge
jarvis_mt5_connected {1 if MT5_AVAILABLE and dashboard_data.mt5_manager and dashboard_data.mt5_manager.is_connected() else 0}
"""
    
    # Add account balance if available
    account_info = dashboard_data.get_mt5_account_info()
    if account_info:
        metrics_text += f"""
# HELP jarvis_account_balance MT5 account balance
# TYPE jarvis_account_balance gauge
jarvis_account_balance {account_info['balance']}

# HELP jarvis_account_equity MT5 account equity
# TYPE jarvis_account_equity gauge
jarvis_account_equity {account_info['equity']}
"""
    
    return app.response_class(metrics_text, mimetype="text/plain; version=0.0.4")

@app.route("/ab")
def ab():
    """A/B testing endpoint (legacy)"""
    con = sqlite3.connect(dashboard_data.db_path)
    c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS policy_experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        ts INT, symbol TEXT, policy TEXT, realized REAL)""")
    c.execute("""SELECT policy, COUNT(*), 
                       SUM(CASE WHEN realized>0 THEN 1 ELSE 0 END)*1.0/COUNT(*), 
                       AVG(realized), SUM(realized) 
                FROM policy_experiments 
                GROUP BY policy ORDER BY SUM(realized) DESC""")
    rows = c.fetchall()
    con.close()
    
    data = [{"policy": r[0], "n": r[1], "winrate": r[2], "avg£": r[3], "pnl£": r[4]} for r in rows]
    return jsonify(data)

if __name__ == "__main__":
    # Create templates directory and basic template if they don't exist
    import os
    os.makedirs('templates', exist_ok=True)
    
    # Run the Flask app
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    print(f"Starting JARVIS Dashboard on http://{host}:{port}")
    print(f"MT5 Available: {MT5_AVAILABLE}")
    
    app.run(host=host, port=port, debug=debug)
