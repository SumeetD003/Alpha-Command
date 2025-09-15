from datetime import datetime, timedelta, timezone
from functools import partial

from ._stats import compute_stats
from .backtesting import Backtest, Strategy
from .livebroker import LiveBroker
from ._util import _as_str, _Indicator, _Data, try_
import pandas as pd
class Forwardtest(Backtest):
    def __init__(self,strategy,symbol,start,end,
                 cash=10_000, 
                 commission=0.0, 
                 holding: dict = {},
                 margin: float = 1.,
                 trade_on_close=False,
                 hedging=False,
                 exclusive_orders=False,
                 trade_start_date=None,
                 lot_size=1,
                 fail_fast=True,
                 storage: dict | None = None,
                 is_option: bool = False ,
                 broker_aggregator=None, 
                 timeframe='1m'):
        self.broker_aggregator = broker_aggregator
        self.symbol=symbol
        self.start=start
        self.end=end
        self.timeframe = timeframe
        start_time = datetime.now(timezone.utc)
        data = self.broker_aggregator.fetch_data(self.symbol, start - timedelta(days=1), start_time, self.timeframe)
        print(data)
        
        super().__init__(data, strategy, cash=cash, commission=commission, margin=margin, 
                         trade_on_close=trade_on_close, hedging=hedging, exclusive_orders=exclusive_orders,
                         trade_start_date=trade_start_date,
                        lot_size=lot_size,
                        fail_fast=fail_fast,
                        storage = storage,
                        is_option = is_option)
        self._broker = partial(LiveBroker,cash=cash, holding=holding, commission=commission, margin=margin,
                            trade_on_close=trade_on_close, hedging=hedging, exclusive_orders=exclusive_orders,
                            trade_start_date=trade_start_date, lot_size=lot_size, fail_fast=fail_fast, storage=storage,
                            is_option=is_option, broker_aggregator=broker_aggregator, timeframe=timeframe)

    def run_live(self):
        data = _Data(self._data.copy(deep=False))
        broker = self._broker(data=data, symbol=self.symbol)
        
        #broker.fetch_data(symbol, start - timedelta(days=1), start_time)
        strategy = self._strategy(broker, data, {})

        strategy.init()
        data._update()  # Strategy.init might have changed/added to data.df
        equity_curve = []
        start_time = datetime.now(timezone.utc)
        while start_time < self.end:
            print(f"Fetching data for {self.symbol} from {self.start - timedelta(days=1)} to {start_time}")
            broker.fetch_data(self.symbol, self.start - timedelta(days=1), start_time)
            print("Data fetched")
            data._set_length(len(data.Close))
            data._update()  # Ensure the strategy has the latest data
            broker.wait_for_next_candle()
            broker.next()
            strategy.next()
            equity_curve.append(broker.equity)
            print("Orders waiting for execution")
            
            print(f"Orders after strategy next: {broker.orders} eq {broker.equity}")
            start_time += timedelta(seconds=broker._get_timeframe_seconds(self.timeframe))
        """
        self._results = compute_stats(
            trades=broker.closed_trades,
            equity=pd.Series(equity_curve, index=data.index),
            ohlc_data=self._data,
            risk_free_rate=0.0,
            strategy_instance=strategy,
        )
        """


