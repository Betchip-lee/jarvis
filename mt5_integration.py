#!/usr/bin/env python3
"""
MT5 Integration Module for JARVIS AI Trading System
Handles all MetaTrader 5 operations for Pepperstone broker
"""

import MetaTrader5 as mt5
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import threading

# Environment variables for MT5 connection
MT5_LOGIN = os.getenv("MT5_LOGIN", "")
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "PepperstoneUK-Live")
MT5_TIMEOUT = int(os.getenv("MT5_TIMEOUT", "10000"))

class MT5Manager:
    """Manages MT5 connection and trading operations for JARVIS"""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.last_error = None
        self.lock = threading.Lock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """Connect to MT5 terminal"""
        with self.lock:
            try:
                # Initialize MT5
                if not mt5.initialize():
                    self.last_error = f"MT5 initialize failed: {mt5.last_error()}"
                    self.logger.error(self.last_error)
                    return False
                
                # Login to account
                if MT5_LOGIN and MT5_PASSWORD:
                    login = int(MT5_LOGIN)
                    if not mt5.login(login, MT5_PASSWORD, MT5_SERVER):
                        self.last_error = f"MT5 login failed: {mt5.last_error()}"
                        self.logger.error(self.last_error)
                        mt5.shutdown()
                        return False
                
                # Get account info
                self.account_info = mt5.account_info()
                if self.account_info is None:
                    self.last_error = "Failed to get account info"
                    self.logger.error(self.last_error)
                    return False
                
                self.connected = True
                self.logger.info(f"Connected to MT5. Account: {self.account_info.login}, Server: {MT5_SERVER}")
                return True
                
            except Exception as e:
                self.last_error = f"Connection error: {str(e)}"
                self.logger.error(self.last_error)
                return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.logger.info("Disconnected from MT5")
    
    def is_connected(self) -> bool:
        """Check if connected to MT5"""
        return self.connected
    
    def get_account_info(self) -> Optional[Dict]:
        """Get current account information"""
        if not self.connected:
            return None
        
        try:
            info = mt5.account_info()
            if info is None:
                return None
            
            return {
                'login': info.login,
                'balance': info.balance,
                'equity': info.equity,
                'margin': info.margin,
                'free_margin': info.margin_free,
                'margin_level': info.margin_level,
                'profit': info.profit,
                'currency': info.currency,
                'leverage': info.leverage
            }
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information"""
        if not self.connected:
            return None
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None
            
            tick = mt5.symbol_info_tick(symbol)
            
            return {
                'symbol': symbol,
                'bid': tick.bid if tick else 0,
                'ask': tick.ask if tick else 0,
                'spread': info.spread,
                'digits': info.digits,
                'point': info.point,
                'min_lot': info.volume_min,
                'max_lot': info.volume_max,
                'lot_step': info.volume_step,
                'currency_base': info.currency_base,
                'currency_profit': info.currency_profit,
                'trade_mode': info.trade_mode
            }
        except Exception as e:
            self.logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def place_order(self, symbol: str, action: str, volume: float, 
                   price: float = None, sl: float = None, tp: float = None,
                   comment: str = "JARVIS AI") -> Dict:
        """
        Place a trading order
        action: 'buy' or 'sell'
        """
        if not self.connected:
            return {'success': False, 'error': 'Not connected to MT5'}
        
        with self.lock:
            try:
                # Get symbol info
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    return {'success': False, 'error': f'Symbol {symbol} not found'}
                
                # Enable symbol if needed
                if not symbol_info.visible:
                    if not mt5.symbol_select(symbol, True):
                        return {'success': False, 'error': f'Failed to select {symbol}'}
                
                # Get current price if not provided
                if price is None:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick is None:
                        return {'success': False, 'error': f'Failed to get price for {symbol}'}
                    price = tick.ask if action.lower() == 'buy' else tick.bid
                
                # Determine order type
                order_type = mt5.ORDER_TYPE_BUY if action.lower() == 'buy' else mt5.ORDER_TYPE_SELL
                
                # Prepare request
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": order_type,
                    "price": price,
                    "deviation": 20,
                    "magic": 12345,  # JARVIS magic number
                    "comment": comment,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                # Add stop loss and take profit if provided
                if sl is not None:
                    request["sl"] = sl
                if tp is not None:
                    request["tp"] = tp
                
                # Send order
                result = mt5.order_send(request)
                
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    error_msg = f"Order failed: {result.retcode} - {result.comment}"
                    self.logger.error(error_msg)
                    return {'success': False, 'error': error_msg, 'retcode': result.retcode}
                
                self.logger.info(f"Order successful: {result.order} - {action} {volume} {symbol} at {price}")
                return {
                    'success': True,
                    'order_id': result.order,
                    'volume': volume,
                    'price': result.price,
                    'comment': result.comment
                }
                
            except Exception as e:
                error_msg = f"Order execution error: {str(e)}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        if not self.connected:
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'buy' if pos.type == mt5.ORDER_TYPE_BUY else 'sell',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'time': datetime.fromtimestamp(pos.time),
                    'comment': pos.comment,
                    'swap': pos.swap,
                    'commission': pos.commission
                })
            
            return position_list
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def close_position(self, ticket: int) -> Dict:
        """Close a specific position"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected to MT5'}
        
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return {'success': False, 'error': f'Position {ticket} not found'}
            
            pos = position[0]
            
            # Prepare close request
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(pos.symbol)
            close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "price": close_price,
                "deviation": 20,
                "magic": 12345,
                "comment": "JARVIS Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Close failed: {result.retcode} - {result.comment}"
                return {'success': False, 'error': error_msg}
            
            self.logger.info(f"Position {ticket} closed successfully")
            return {'success': True, 'order_id': result.order, 'profit': pos.profit}
            
        except Exception as e:
            error_msg = f"Close position error: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def get_history_orders(self, days: int = 7) -> List[Dict]:
        """Get historical orders"""
        if not self.connected:
            return []
        
        try:
            from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            from_date = from_date.timestamp() - (days * 24 * 3600)
            to_date = datetime.now().timestamp()
            
            orders = mt5.history_orders_get(from_date, to_date)
            if orders is None:
                return []
            
            order_list = []
            for order in orders:
                order_list.append({
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': 'buy' if order.type == mt5.ORDER_TYPE_BUY else 'sell',
                    'volume': order.volume_initial,
                    'price': order.price_open,
                    'time': datetime.fromtimestamp(order.time_setup),
                    'state': order.state,
                    'comment': order.comment
                })
            
            return order_list
            
        except Exception as e:
            self.logger.error(f"Error getting history orders: {e}")
            return []
    
    def get_history_deals(self, days: int = 7) -> List[Dict]:
        """Get historical deals (executed trades)"""
        if not self.connected:
            return []
        
        try:
            from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            from_date = from_date.timestamp() - (days * 24 * 3600)
            to_date = datetime.now().timestamp()
            
            deals = mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return []
            
            deal_list = []
            for deal in deals:
                deal_list.append({
                    'ticket': deal.ticket,
                    'order': deal.order,
                    'symbol': deal.symbol,
                    'type': 'buy' if deal.type == mt5.DEAL_TYPE_BUY else 'sell',
                    'volume': deal.volume,
                    'price': deal.price,
                    'commission': deal.commission,
                    'swap': deal.swap,
                    'profit': deal.profit,
                    'time': datetime.fromtimestamp(deal.time),
                    'comment': deal.comment
                })
            
            return deal_list
            
        except Exception as e:
            self.logger.error(f"Error getting history deals: {e}")
            return []
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols"""
        if not self.connected:
            return []
        
        try:
            symbols = mt5.symbols_get()
            if symbols is None:
                return []
            
            # Filter for tradeable symbols
            tradeable_symbols = []
            for symbol in symbols:
                if symbol.visible and symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                    tradeable_symbols.append(symbol.name)
            
            return sorted(tradeable_symbols)
            
        except Exception as e:
            self.logger.error(f"Error getting available symbols: {e}")
            return []
    
    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for a symbol"""
        if not self.connected:
            return False
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False
            
            return symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
            
        except Exception as e:
            self.logger.error(f"Error checking market status for {symbol}: {e}")
            return False
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.connected:
            self.disconnect()

# Global MT5 manager instance
mt5_manager = MT5Manager()

def get_mt5_manager() -> MT5Manager:
    """Get the global MT5 manager instance"""
    return mt5_manager

def ensure_mt5_connection() -> bool:
    """Ensure MT5 connection is established"""
    if not mt5_manager.is_connected():
        return mt5_manager.connect()
    return True