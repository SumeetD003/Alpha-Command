import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from functools import partial
from .backtesting import Strategy, Backtest, _Broker
from .broker_aggregator.aggregator import BrokerAggregator

class LiveBroker(_Broker):
    def __init__(self, data, cash, holding, commission, margin, trade_on_close, hedging, exclusive_orders,
                 trade_start_date, lot_size, fail_fast, storage,is_option, broker_aggregator, timeframe, symbol):
        super().__init__(data=data, cash=cash, commission=commission, margin=margin, 
                         trade_on_close=trade_on_close, hedging=hedging, 
                         exclusive_orders=exclusive_orders, holding = holding, trade_start_date = trade_start_date,
                         lot_size = lot_size, fail_fast = fail_fast, storage = storage,is_option = is_option)
        self.broker_aggregator = broker_aggregator
        self.timeframe = timeframe
        self.symbol = symbol

    def fetch_data(self, symbol, start, end):
        if self.broker_aggregator:
            new_data = self.broker_aggregator.fetch_data(symbol, start, end, self.timeframe)
            self._update_data(new_data)

    def place_order(self, size, limit=None, stop=None, sl=None, tp=None, tag=None, trade=None):
        print("place order function called")
        if self.broker_aggregator:
            order_type = 'BUY' if size > 0 else 'SELL'
            print(f"Placing {order_type} order for {self.symbol} with volume {abs(size)}")
            order_id=self.broker_aggregator.place_order(symbol=self.symbol, volume=abs(size), order_type=order_type)
        return order_id

    def _update_data(self, new_data):
        new_df = pd.DataFrame(new_data)
        new_df.index = pd.to_datetime(new_df.index)
        combined_df = pd.concat([self._data.df, new_df]).drop_duplicates().sort_index()
        self._data._df = combined_df  # Update the internal dataframe directly
        self._data._update()  # Update internal structures

    def wait_for_next_candle(self):
        timeframe_seconds = self._get_timeframe_seconds(self.timeframe)
        now = datetime.now(timezone.utc)
        next_candle_time = (now + timedelta(seconds=timeframe_seconds)).replace(second=0, microsecond=0)
        time_to_wait = (next_candle_time - now).total_seconds()
        time.sleep(time_to_wait)

    def _get_timeframe_seconds(self, timeframe):
        if timeframe.endswith('m'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 3600
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 86400
        else:
            raise ValueError('Unsupported timeframe')

    def next(self):
        print("LiveBroker next() called")
        
        self._execute_live_orders()
        super().next()

    def _execute_live_orders(self):
        print(f"Live orders before execution: {self.orders}")
        for order in self.orders.copy():  # Use a copy to modify the list while iterating
            if not order.is_contingent:
                print(f"Executing order: {order}")
                self.place_order(order.size, order.limit, order.stop, order.sl, order.tp, order.tag, order.parent_trade)
                #self.orders.remove(order)
        print(f"Live orders after execution: {self.orders}")