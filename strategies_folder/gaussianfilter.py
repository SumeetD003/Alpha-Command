import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import warnings
import numpy as np
import pandas as pd
import pandas_ta as ta

import math
import csv
import io

from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import GOOG
from TradeMaster.risk_management.rpt import RiskPerTrade
#from TradeMaster.trade_management.trade_manager import TradeManager
from TradeMaster.trade_management.tp_sl.swing_high_low_tm import Swing_High_Low
from TradeMaster.trade_management.tp_sl.atr_tm import ATR_RR_TradeManagement
#from TradeMaster.trade_management.level_distribution.swing_atr_multi_tp_sl import TradeLevelsCalculator  
#from TradeMaster.trade_management.weight_distribution.atr_equal_weight import EqualWeightedDistribution

class GaussianChannelStrategy(Strategy):    
    atr_multiplier = 1.5  
    atr_period = 14
    current_amount = 10000
    adx_period = 14
    initial_risk_per_trade = 0.1
    profit_risk_percentage = 0.01
    atr_period = 14
    atr_multiplier = 3
    swing_length = 6
    risk_reward_ratio = 2

    def init(self):
        """Initialize indicators and management strategies"""
        hlc3 = (self.data.High + self.data.Low + self.data.Close) / 3
        
        def calculate_gaussian():
            beta = (1 - np.cos(2 * np.pi / 144)) / (np.sqrt(2) - 1)
            alpha = -beta + np.sqrt(beta ** 2 + 2 * beta)
            ema_length = int(2 / alpha - 1) if alpha != 0 else 20
            return ta.ema(pd.Series(hlc3), length=ema_length).ffill().values
        self.gaussian = self.I(calculate_gaussian)
        
        def calculate_atr():
            return ta.atr(pd.Series(self.data.High), pd.Series(self.data.Low), 
                         pd.Series(self.data.Close), length=14).ffill().values
        self.atr = self.I(calculate_atr)
        
        def calculate_stoch():
            stoch = ta.stochrsi(pd.Series(self.data.Close), length=14, rsi_length=14, k=3, d=3)
            return stoch['STOCHRSIk_14_14_3_3'].ffill().values
        self.stoch_k = self.I(calculate_stoch)
        
        self.high_band = self.I(lambda: self.gaussian + self.atr * 1.414)
        self.low_band = self.I(lambda: self.gaussian - self.atr * 1.414)
        
        # Initialize trade management strategy
        self.trade_management_strategy = Swing_High_Low(
            self,
            swing_length=self.swing_length,
            risk_reward_ratio=self.risk_reward_ratio
        )  
        
        # Initialize risk management strategy
        self.risk_management_strategy = RiskPerTrade(
            self,
            initial_risk_per_trade=self.initial_risk_per_trade,
            profit_risk_percentage=self.profit_risk_percentage
        )

        
        
        self.total_trades = len(self.closed_trades)
        self.active_trades = {}
        self.trade_counter = 0
        self.trade_details = {}

    def next(self):
        """Main trading logic"""
        self.on_trade_close()
        
        if len(self.data.Close) < 50:
            return

        price_above_band = self.data.Close[-1] > self.high_band[-1]
        gaussian_rising = self.gaussian[-1] > self.gaussian[-2]
        stoch_overbought = self.stoch_k[-1] > 70

        if price_above_band and gaussian_rising and stoch_overbought:
            if self.position().is_short:
                self.position().close()
            if not self.position():
                self.add_buy_trade()

        current_price = self.data.Close[-1]
        trades_to_close = []

        for trade_id, trade_info in list(self.active_trades.items()):
            sl_levels = trade_info['sl_levels']
            tp_levels = trade_info['tp_levels']
            remaining_size = trade_info['remaining_size']
            original_size = trade_info['original_size']

            furthest_sl = min([list(sl.keys())[0] for sl in sl_levels])
            if current_price <= furthest_sl:
                self.sell(size=remaining_size)
                self.trade_details[trade_id]['booked'].append({'price': current_price, 'size': remaining_size, 'type': 'SL'})
                trades_to_close.append(trade_id)
                print(f"Trade {trade_id} closed at SL: {current_price}")
                continue

            for i, tp_dict in enumerate(tp_levels):
                tp_level = list(tp_dict.keys())[0]
                weight = list(tp_dict.values())[0]
                if current_price >= tp_level and weight > 0 and remaining_size > 0:
                    close_size = int(original_size * weight)
                    if close_size > remaining_size:
                        close_size = remaining_size
                    if close_size > 0:
                        self.sell(size=close_size)
                        self.trade_details[trade_id]['booked'].append({'price': current_price, 'size': close_size, 'type': 'TP'})
                        trade_info['remaining_size'] -= close_size
                        tp_levels[i] = {tp_level: 0}
                        print(f"Trade {trade_id} closed {close_size} units at TP: {tp_level}")

            if trade_info['remaining_size'] <= 0:
                trades_to_close.append(trade_id)

        for trade_id in trades_to_close:
            del self.active_trades[trade_id]

        if self.position() and self.data.Close[-1] < self.gaussian[-1]:
            self.position().close()
            if self.active_trades:
                last_trade_id = max(self.active_trades.keys())
                remaining_size = self.active_trades[last_trade_id]['remaining_size']
                self.trade_details[last_trade_id]['booked'].append({'price': current_price, 'size': remaining_size, 'type': 'Manual Exit'})
            self.active_trades.clear()

    def add_buy_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(direction="buy")
            stop_loss_perc = (entry - stop_loss) / entry
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            self.buy(size=qty, sl=stop_loss, tp=take_profit)

    def on_trade_close(self):
        """Handle closed trades"""
        num_closed = len(self.closed_trades) - self.total_trades
        if num_closed > 0:
            for trade in self.closed_trades[-num_closed:]:
                if trade.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()
        self.total_trades = len(self.closed_trades)

if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    bt = Backtest(GOOG, GaussianChannelStrategy, cash=100000, commission=.002, margin=0.01)
    stats = bt.run()
    
    bt.plot()
    print(stats)
    
    bt.tear_sheet()