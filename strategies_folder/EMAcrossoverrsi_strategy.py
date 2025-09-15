import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
#from TradeMaster.trade_management.tp_sl.atr_tm import Single_tp_sl
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.risk_management.rpt import RiskPerTrade
from TradeMaster.trade_management.tp_sl.std_dev import Single_tp_sl
from TradeMaster.test import GOOG
import pandas_ta as ta
import pandas as pd
import warnings
import math

class SmaCross(Strategy):
    sma10 = 10
    sma60 = 60
    std_dev_multiplier = 2
    std_dev_period = 16

    risk_reward_ratio=1.5
    atr_multiplier=3
    initial_risk_per_trade=0.01
    atr_period = 14


    def init(self):
        close_series = pd.Series(self.data.Close, index=self.data.index)
        self.sma10 = self.I(ta.sma, close_series, self.sma10)
        self.sma60 = self.I(ta.sma, close_series, self.sma60)
        self.trade_management_strategy = Single_tp_sl(self, self.risk_reward_ratio, self.std_dev_multiplier,self.std_dev_period)
        #self.trade_management_strategy = Single_tp_sl(self, risk_reward_ratio=self.risk_reward_ratio, atr_multiplier=self.atr_multiplier, atr_period=self.atr_period)
        #self.risk_management_strategy = EqualRiskManagement(self, initial_risk_per_trade=self.initial_risk_per_trade)
        #self.risk_management_strategy = KellyRiskManagement(self,self.initial_risk_per_trade, self.current_amount)
        #self.risk_management_strategy =VolatilityBasedPositionSizing(self, self.initial_risk_per_trade, target_var=0.015)
        self.risk_management_strategy = RiskPerTrade(self,self.initial_risk_per_trade, profit_risk_percentage = 0.02)
        
        self.total_trades = len(self.closed_trades)

        self.total_trades = len(self.closed_trades)


    def next(self):
        self.on_trade_close()

        if self.sma10[-1] > self.sma60[-1]:  
            if self.position().is_short:
                self.position().close() 
            if not self.position(): 
                self.add_buy_trade()
        elif self.sma10[-1] < self.sma60[-1]:  
            if self.position().is_long:
                self.position().close() 
            if not self.position():  
                self.add_sell_trade()


    def add_buy_trade(self):
        risk_per_trade = self.initial_risk_per_trade
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss = entry - (self.std_dev_multiplier * self.data.Close[-self.std_dev_period:].std())
            take_profit = entry + (self.risk_reward_ratio * (entry - stop_loss))
            stop_loss_perc = (entry - stop_loss) / entry
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            self.buy(size=qty, sl=stop_loss, tp=take_profit)

    def add_sell_trade(self):
        risk_per_trade = self.initial_risk_per_trade
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss = entry + (self.std_dev_multiplier * self.data.Close[-self.std_dev_period:].std())
            take_profit = entry - (self.risk_reward_ratio * (stop_loss - entry))
            stop_loss_perc = (stop_loss - entry) / entry
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            self.sell(size=qty, sl=stop_loss, tp=take_profit)
    def on_trade_close(self):
        num_of_trades_closed = len(self.closed_trades) - self.total_trades
        if num_of_trades_closed > 0:
            for trade in self.closed_trades[-num_of_trades_closed:]:
                if trade.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()
        self.total_trades = len(self.closed_trades)
        
        
if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)

    # Run the backtest
    bt = Backtest(GOOG, SmaCross, cash=100000, commission=0.002, margin=0.0001)
    stats = bt.run()
    bt.plot()
    print(stats)
    print(stats['_trades'])
    bt.tear_sheet()