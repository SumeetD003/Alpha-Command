import ccxt
from .base import BaseBroker

class CCXTBroker(BaseBroker):
    def __init__(self, exchange_name, use_testnet=False):
        self.exchange_name = exchange_name
        self.use_testnet = use_testnet
        self.exchange = None
    
    def connect(self, api_key, secret, *args, **kwargs):
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
            'timeout': 30000,
            'enableRateLimit': True,
        })
        
        if self.use_testnet and self.exchange_name == 'binance':
            self.exchange.set_sandbox_mode(True)
            self.exchange.urls['api'] = self.exchange.urls['test']

    def get_balance(self):
        return self.exchange.fetch_balance()
    
    def place_order(self, symbol, volume, order_type, price=None, sl=None, tp=None, comment=""):
        if order_type.lower() == 'buy':
            side = 'buy'
        elif order_type.lower() == 'sell':
            side = 'sell'
        else:
            raise ValueError("Invalid order type")

        order = {
            'symbol': symbol,
            'type': 'limit' if price else 'market',
            'side': side,
            'amount': volume,
        }
        if price:
            order['price'] = price
        
        return self.exchange.create_order(**order)
    
    def get_order(self, order_id, symbol=None):
        return self.exchange.fetch_order(order_id, symbol)
    
    def cancel_order(self, order_id, symbol=None):
        return self.exchange.cancel_order(order_id, symbol)
    
    def get_open_orders(self, symbol=None):
        return self.exchange.fetch_open_orders(symbol)
    
    def get_trade_history(self, symbol=None):
        return self.exchange.fetch_my_trades(symbol)
    
    def get_market_data(self, symbol):
        return self.exchange.fetch_ticker(symbol)
    
    def get_positions(self):
        raise NotImplementedError("CCXT does not have a unified positions endpoint")
    
    def get_account_info(self):
        raise NotImplementedError("CCXT does not have a unified account info endpoint")
