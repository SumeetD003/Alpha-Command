from datetime import datetime, timedelta
import time

import pandas as pd
import pytz
from .base import BaseBroker
import MetaTrader5 as mt5

class MT5Broker(BaseBroker):
    def login(self, account_id, password, server):
        """Login to MT5 account"""
        session = mt5.login(account_id, password=password, server=server)
        if not session:
            print("Login failed, error code =", mt5.last_error())
        else:
            print("Logged in", session)
    
    def connect(self, account_id, password, server, path=None, *args, **kwargs):
        if path is not None:
            if not mt5.initialize(path):
                print("Initialize() failed, error code =", mt5.last_error())
        else:
            if not mt5.initialize():
                print("Initialize() failed, error code =", mt5.last_error())
        self.login(account_id, password, server)
    
    def get_balance(self):
        """Get available account balance"""
        account_info = mt5.account_info()
        if account_info is None:
            print("Failed to get account balance, error code =", mt5.last_error())
            return None
        else:
            return account_info.balance
    def fetch_data(self, symbol, start, end, timeframe,*args, **kwargs):
        """Fetch historical data for a given symbol and timeframe"""
        timeframe_dict = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1,
            '1w': mt5.TIMEFRAME_W1,
            '1mo': mt5.TIMEFRAME_MN1,
        }
        mt5_timeframe = timeframe_dict.get(timeframe)
        if not mt5_timeframe:
            print("Unsupported timeframe")
            return None
        current_time = datetime.now(pytz.utc) + timedelta(hours=3)
        
        rates = mt5.copy_rates_from(symbol, mt5_timeframe, current_time, 9999)
        #rates = mt5.copy_rates_range(symbol, mt5_timeframe, start, end)
        if rates is None:
            print("Failed to fetch data, error code =", mt5.last_error())
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'real_volume': 'Volume'  # Renaming tick_volume to Volume
        }, inplace=True)
        return df


    def get_symbol_info(self, symbol):
        """Get information about a symbol"""
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"Failed to get symbol info for {symbol}, error code =", mt5.last_error())
            return None
        else:
            return info
    def place_order(self, symbol, volume,order_type, price=None, sl=None, tp=None, comment=""):
        """Place an order with optional SL and TP"""
        order_dict = {
            "buy": mt5.ORDER_TYPE_BUY,
            "sell": mt5.ORDER_TYPE_SELL
        }
        order_type = order_dict.get(order_type.lower())
        if order_type is None:
            print("Invalid order type")
            return

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid,
            #"sl": sl,
            #"tp": tp,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,  # Good till cancel
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if price is not None:
            request["price"] = price

        result = mt5.order_send(request)
        time.sleep(2)
        print(result)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print("Order failed, retcode =", result.retcode)
        else:
            return result
    
    def get_order(self, order_id):
        return mt5.history_orders_get(ticket=order_id)
    
    def cancel_order(self, order_id):
        order_id=int(order_id)
        request = {
            "action" : mt5.TRADE_ACTION_REMOVE ,
            "order" : order_id ,
        }
        result=mt5.order_send(request)
        time.sleep(2)
        print(result)
        try:
            if result.retcode != 10009:
                print(f"Failed to cancel order: {result.comment}")
                print(result)
                #return False
            else:
                print(f"Order {order_id} canceled successfully")
        except Exception as e:
            print(e)
    
    def get_open_orders(self):
        return mt5.orders_get()
    
    def get_trade_history(self):
        return mt5.history_deals_get()
    
    def get_market_data(self, symbol):
        return mt5.symbol_info_tick(symbol)
    
    def get_positions(self):
        return mt5.positions_get()
    
    def get_account_info(self):
        return mt5.account_info()
