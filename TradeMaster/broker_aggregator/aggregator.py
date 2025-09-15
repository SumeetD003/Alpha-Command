from ..broker_aggregator.brokers.mt5 import MT5Broker
from ..broker_aggregator.brokers.ccxt_broker import CCXTBroker
# from brokers.binance import BinanceBroker
# from brokers.bybit import BybitBroker
# from brokers.ib_insync import IBInsyncBroker
# from brokers.zerodha import ZerodhaBroker
# from brokers.angel import AngelBroker

class BrokerAggregator:
    def __init__(self):
        self.brokers = {
            'mt5': MT5Broker(),
            'ccxt_binance': CCXTBroker('binance'),
            'ccxt_binance_testnet': CCXTBroker('binance', use_testnet=True),
            'ccxt_bybit': CCXTBroker('bybit'),
            # 'ib_insync': IBInsyncBroker(),
            # 'zerodha': ZerodhaBroker(),
            # 'angel': AngelBroker(),
        }
        self.active_broker = None
    
    def set_active_broker(self, broker_name, *args, **kwargs):
        self.active_broker = self.brokers.get(broker_name)
        if self.active_broker:
            self.active_broker.connect(*args, **kwargs)
        else:
            print(f"Broker {broker_name} not found")
    def fetch_data(self,*args, **kwargs):
        if self.active_broker:
            return self.active_broker.fetch_data(*args, **kwargs)
        else:
            print("No active broker set")
    def get_balance(self):
        if self.active_broker:
            return self.active_broker.get_balance()
        else:
            print("No active broker set")
    
    def place_order(self, symbol, volume, order_type, price=None, sl=None, tp=None, comment=""):
        if self.active_broker:
            print("placing order now")
            return self.active_broker.place_order(symbol, volume, order_type, price, sl, tp, comment)
        else:
            print("No active broker set")
    def get_order(self, order_id):
        if self.active_broker:
            return self.active_broker.get_order(order_id)
        else:
            print("No active broker set")
    
    def cancel_order(self, order_id):
        if self.active_broker:
            return self.active_broker.cancel_order(order_id)
        else:
            print("No active broker set")
    
    def get_open_orders(self):
        if self.active_broker:
            return self.active_broker.get_open_orders()
        else:
            print("No active broker set")
    
    def get_trade_history(self):
        if self.active_broker:
            return self.active_broker.get_trade_history()
        else:
            print("No active broker set")
    
    def get_market_data(self, symbol):
        if self.active_broker:
            return self.active_broker.get_market_data(symbol)
        else:
            print("No active broker set")
    
    def get_positions(self):
        if self.active_broker:
            return self.active_broker.get_positions()
        else:
            print("No active broker set")
    
    def get_account_info(self):
        if self.active_broker:
            return self.active_broker.get_account_info()
        else:
            print("No active broker set")
