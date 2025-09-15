class BaseBroker:
    def connect(self, *args, **kwargs):
        raise NotImplementedError
    def fetch_data(self):
        raise NotImplementedError
    def get_balance(self):
        raise NotImplementedError
    
    def place_order(self, *args, **kwargs):
        raise NotImplementedError
    
    def get_order(self, order_id):
        raise NotImplementedError
    
    def cancel_order(self, order_id):
        raise NotImplementedError
    
    def get_open_orders(self):
        raise NotImplementedError
    
    def get_trade_history(self):
        raise NotImplementedError
    
    def get_market_data(self, symbol):
        raise NotImplementedError
    
    def get_positions(self):
        raise NotImplementedError
    
    def get_account_info(self):
        raise NotImplementedError
