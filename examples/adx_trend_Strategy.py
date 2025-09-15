import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.wfo import WalkForwardOptimizer
import warnings, time
import math
import pandas as pd
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import GOOG
from TradeMaster.trade_management.single_tp_sl.atr_tm import ATR_RR_TradeManagement
from TradeMaster.risk_management.vps import VolatilityBasedPositionSizing
from TradeMaster.risk_management.portfolio_heat_rm import PortfolioHeatRiskManagement
from TradeMaster.risk_management.frps_general_rm import FixedRatioPositionSizing
from TradeMaster.multi_backtester.multi_backtester_v2 import MultiBacktest
from TradeMaster.risk_management.rpt import RiskPerTrade
from TradeMaster.hyperparameter_optimizer.hyperparameter_optimizer import HyperParameterOptimizer
from TradeMaster.monte_carlo_simulation.monte_carlo_simulation import MonteCarloSimulation
from TradeMaster.cpcv.cpcv import CPCV
import pandas_ta as ta


import importlib
import TradeMaster.multi_backtester.multi_backtester

importlib.reload(TradeMaster.multi_backtester.multi_backtester)

from TradeMaster.multi_backtester.multi_backtester import MultiBacktest

class AdxTrendStrategy(Strategy):
    atr_period = 14
    risk_reward_ratio = 1.25
    atr_multiplier = 3
    initial_risk_per_trade = 0.01
    adx_period=14

    def init(self):
        self.adx = self.I(self.data.df.ta.adx(self.adx_period)[f"ADX_{self.adx_period}"])
        self.trade_management_strategy = ATR_RR_TradeManagement(self, risk_reward_ratio=self.risk_reward_ratio, atr_period=self.atr_period, atr_multiplier=self.atr_multiplier)
        self.risk_management_strategy = RiskPerTrade(self, initial_risk_per_trade= self.initial_risk_per_trade, profit_risk_percentage=0.02)
        self.total_trades = len(self.closed_trades)

    def next(self):
        self.on_trade_close()
        
        if self.adx[-1] > 25:
            if self.data.Close[-1] > self.data.Close[-2]:
                if self.position().is_short:
                    self.position().close()
                if not self.position():
                    self.add_buy_trade()
            elif self.data.Close[-1] < self.data.Close[-2]:
                if self.position().is_long:
                    self.position().close()
                if not self.position():
                    self.add_sell_trade()

    def add_buy_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(direction="buy")
            stop_loss_perc = (entry - stop_loss) / entry
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            self.buy(size=qty, sl=stop_loss, tp=take_profit)

    def add_sell_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(direction="sell")
            stop_loss_perc = (stop_loss - entry) / entry
            trade_size = risk_per_trade / stop_loss_perc # Amount going to invest currently
            qty = math.ceil(trade_size / self.data.Close[-1]) # Lot size, number of stocks bought
            self.sell(size=qty, sl=stop_loss, tp=take_profit)

    def on_trade_close(self):
        num_of_trades_closed = len(self.closed_trades) - self.total_trades
        if num_of_trades_closed > 0:
            for trade in self.closed_trades[-num_of_trades_closed:]:
                if trade.pl < 0:
                    self.risk_management_strategy.update_after_loss() # Parameter update in case strategy suffers a loss, ie stop loss triggered
                else:
                    self.risk_management_strategy.update_after_win() # Parameter update in case strategy make a profit, ie take profit is triggered
        self.total_trades = len(self.closed_trades)







if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    bt = Backtest(GOOG, AdxTrendStrategy, cash=100000, commission=.002)
    print(GOOG)
    stats = bt.run()
    print(stats)
    print(stats['_trades'])
    bt.plot()
    