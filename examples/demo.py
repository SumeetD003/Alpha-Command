import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import math
import pandas as pd
from TradeMaster.backtesting import Strategy
from TradeMaster.helpers.indicators import calculate_atr
from TradeMaster.lib import crossover
from TradeMaster.risk_management.dalembert_rm import DAlembertRiskManagement
from TradeMaster.risk_management.fibonacci_rm import FibonacciRiskManagement
from TradeMaster.risk_management.manhattan_rm import ManhattanRiskManagement
from TradeMaster.risk_management.oscars_grind_rm import OscardsGrindRiskManagement
from TradeMaster.risk_management.Paroli_rm import ParoliRiskManagement
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.risk_management.martingale_rm import MartingaleRiskManagement
from TradeMaster.strategy_selector import StrategySelector
from TradeMaster.test import SMA
from TradeMaster.trade_management.single_tp_sl.atr_tm import ATR_RR_TradeManagement

class SmaCross(Strategy):
    n1 = 20
    n2 = 50

    risk_reward_ratio=1.5
    atr_multiplier=3
    initial_risk_per_trade=0.01

    def init(self):
        self.sma1 = self.I(self.data.df.ta.sma(self.n1))
        self.sma2 = self.I(self.data.df.ta.sma(self.n2))
        self.trade_management_strategy = ATR_RR_TradeManagement(3,1.5)
        self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        self.total_trades=len(self.closed_trades)
        

    def next(self):
        
        self.on_trade_close()
        if crossover(self.sma1, self.sma2):
            self.position().close()
            risk_per_trade = self.risk_management_strategy.get_risk_per_trade(self._broker._cash)
            
            entry=self.data.Close[-1]
            if risk_per_trade > 0:
                stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(df=self.data.df,direction="buy")
                stop_loss_perc = (entry - stop_loss)/entry
                trade_size = risk_per_trade/stop_loss_perc
                qty = math.ceil(trade_size / self.data.Close[-1])
                self.buy(size=qty, sl=stop_loss, tp=take_profit)
        elif crossover(self.sma2, self.sma1):
            self.position().close()
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
        #print(num_of_trades_closed,i)
        self.total_trades=len(self.closed_trades)

from TradeMaster.backtesting import Backtest
from TradeMaster.test import GOOG

bt = Backtest(GOOG,SmaCross,cash=10000, commission=.002, exclusive_orders=True)
stats = bt.run()
bt.plot()
print(stats)