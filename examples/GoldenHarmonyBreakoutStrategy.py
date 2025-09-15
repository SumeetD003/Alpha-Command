import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import math

import pandas as pd
import numpy as np
import pandas_ta as ta
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.test import GOOG, SMA
from TradeMaster.trade_management.single_tp_sl.atr_tm import ATR_RR_TradeManagement

# Helper function to calculate the Fibonacci levels
def calculate_fib(high, low):
    fib_618 = high - (high - low) * 0.618
    fib_65 = high - (high - low) * 0.65
    return fib_618, fib_65

# Define the strategy class
class GoldenHarmonyBreakoutStrategy(Strategy):
    # Define strategy parameters
    atr_multiplier = 3
    risk_reward_ratio = 1.5
    initial_risk_per_trade = 0.1
    slow_moving_average=9
    fast_moving_average=21
    def init(self):
        self.fast_ema = self.I(self.data.df.ta.ema(self.slow_moving_average))
        self.slow_ema = self.I(self.data.df.ta.ema(self.fast_moving_average)) 

        # Trade and risk management strategies
        self.trade_management_strategy = ATR_RR_TradeManagement(atr_multiplier=self.atr_multiplier, risk_to_reward_ratio=self.risk_reward_ratio)
        self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        self.total_trades = len(self.closed_trades)

        # Initialize tracking for Fibonacci levels
        self.low = np.nan
        self.high = np.nan
        self.first_crossover = False

    def next(self):
        self.on_trade_close()
        current_price = self.data.Close[-1]

        # Get the last values of the EMAs
        prev_fast_ema = self.fast_ema[-2]
        curr_fast_ema = self.fast_ema[-1]
        prev_slow_ema = self.slow_ema[-2]
        curr_slow_ema = self.slow_ema[-1]

        # Check for crossover (fast EMA crossing slow EMA)
        if prev_fast_ema < prev_slow_ema and curr_fast_ema > curr_slow_ema:
            if not self.first_crossover:
                # If this is the first crossover, initialize low and high
                self.low = current_price
                self.high = current_price
                self.first_crossover = True
            else:
                # Update the low and high values after the first crossover
                self.low = min(self.low, current_price)
                self.high = max(self.high, current_price)
        elif prev_fast_ema > prev_slow_ema and curr_fast_ema < curr_slow_ema:
            # Reset the Fibonacci levels when the fast EMA crosses below the slow EMA
            self.low = self.high = np.nan
            self.first_crossover = False

        # Calculate Fibonacci levels if low and high are set
        if not np.isnan(self.low) and not np.isnan(self.high):
            fib_618, fib_65 = calculate_fib(self.high, self.low)
        else:
            fib_618 = fib_65 = np.nan

        # Signal generation logic based on Fibonacci levels
        prev_close = self.data['Close'][-2]
        curr_close = self.data['Close'][-1]

        # Buy signal: when the price crosses above the Fibonacci 0.618 level
        if not np.isnan(fib_618) and prev_close < fib_618 and curr_close > fib_618:
            if self.position() and self.position().is_short:
                self.position().close()  # Close any short position before going long
            if not self.position():
                self.add_buy_trade()

        # Sell signal: when the price crosses below the Fibonacci 0.618 level
        elif not np.isnan(fib_618) and prev_close > fib_618 and curr_close < fib_618:
            if self.position() and self.position().is_long:
                self.position().close()  # Close any long position before going short
            if not self.position():
                self.add_sell_trade()
    def add_buy_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade(self._broker._cash)            
        entry=self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(df=self.data.df,direction="buy")
            stop_loss_perc = (entry - stop_loss)/entry
            trade_size = risk_per_trade/stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            self.buy(size=qty, sl=stop_loss, tp=take_profit)
    def add_sell_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade(self._broker._cash)
        entry=self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(df=self.data.df,direction="sell")
            stop_loss_perc = (stop_loss - entry)/entry
            trade_size = risk_per_trade/stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            self.sell(size=qty, sl=stop_loss, tp=take_profit)
    def on_trade_close(self):
        num_of_trades_closed=len(self.closed_trades)-self.total_trades
        i=0
        if(num_of_trades_closed>0):
            for trade in self.closed_trades[-num_of_trades_closed:]:
                i+=1
                if trade.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()
        self.total_trades=len(self.closed_trades)

bt = Backtest(GOOG, GoldenHarmonyBreakoutStrategy, cash=100000, commission=.002,margin=1/100)
stats = bt.run()
bt.plot()
print(stats)
