import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import math
import pandas as pd
import pandas_ta as ta
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import GOOG
from TradeMaster.trade_management.level_distribution.new_atr_tp_sl import TradeLevelsCalculator
from TradeMaster.risk_management.efficiency_ratio_rm import EfficiencyRatio
from TradeMaster.risk_engine.Single_Risk_Engine import RiskEngine
#from TradeMaster.risk_engine.Multi_Risk_Engine import MultiRiskEngine
from TradeMaster.trade_management.tp_sl.swing_high_low_tm import Swing_High_Low
from TradeMaster.trade_management.trade_manager import TradeManager
from TradeMaster.trade_management.weight_distribution.swing_equal_weight import EqualWeightedDistribution
from TradeMaster.trade_management.trade_manager import TradeManager

from TradeMaster.trade_management.level_distribution.swing_atr_multi_tp_sl import TradeLevelsCalculator  

class AdxTrendStrategy(RiskEngine):
    adx_period = 14
    initial_risk_per_trade = 0.01
    profit_risk_percentage = 0.01
    atr_period = 14
    atr_multiplier = 3
    swing_length = 6
    risk_reward_ratio = 1.5
    
    
    def init(self):
        super().init()
        self.adx = self.I(self.data.df.ta.adx(self.adx_period)[f"ADX_{self.adx_period}"])
        self.trade_management_strategy = Swing_High_Low(self, swing_length=self.swing_length, risk_reward_ratio=self.risk_reward_ratio)  # Explicitly set Swing_High_Low
        self.risk_management_strategy = EfficiencyRatio(self, initial_risk_per_trade=self.initial_risk_per_trade, profit_risk_percentage=self.profit_risk_percentage)
    def next(self):
        
        super().next()
        
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

if __name__ == "__main__":
    bt = Backtest(GOOG, AdxTrendStrategy, cash=1000000, commission=0, margin=0.001)
    stats = bt.run()
    bt.plot()
    print(stats)
    print(stats['_trades'])
    bt.tear_sheet()
