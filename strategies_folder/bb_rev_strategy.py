import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import math
import pandas as pd
import warnings
import pandas_ta as ta
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import GOOG
from TradeMaster.trade_management.level_distribution.new_atr_tp_sl import TradeLevelsCalculator
#from TradeMaster.trade_management.level_distribution.swing_atr_multi_tp_sl import TradeLevelsCalculator
from TradeMaster.risk_management.efficiency_ratio_rm import EfficiencyRatio
from TradeMaster.risk_engine.Multi_Risk_Engine import MultiRiskEngine
#from TradeMaster.trade_management.tp_sl.swing_high_low_tm import Swing_High_Low
from TradeMaster.trade_management.tp_sl.atr_tm import ATR_RR_TradeManagement
#from TradeMaster.trade_management.tp_sl.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.trade_manager import TradeManager
from TradeMaster.trade_management.weight_distribution.atr_equal_weight import EqualWeightedDistribution
#from TradeMaster.trade_management.weight_distribution.swing_equal_weight import EqualWeightedDistribution
from TradeMaster.trade_management.trade_manager import TradeManager
#from TradeMaster.risk_engine.Single_Risk_Engine import RiskEngine


def calculate_bollinger_bands(close,n,dev):
        bbands=ta.bbands(close,n,dev)
        return bbands.to_numpy().T[:3]
class BollingerBandsMeanReversion(MultiRiskEngine):
    n = 20
    dev = 2
    risk_reward_ratio = 1
    initial_risk_per_trade = 0.01
    atr_period = 14
    atr_multiplier = 3
    profit_risk_percentage = 0.01
    swing_length = 6
    n_tp_levels = 4
    n_sl_levels = 4
    def init(self):
        super().init()
        self.bbands = self.I(calculate_bollinger_bands, pd.Series(self.data.Close), self.n, self.dev)
        self.bb_upper, self.bb_middle, self.bb_lower = self.bbands[0],self.bbands[1],self.bbands[2]
        self.trade_management_strategy = ATR_RR_TradeManagement(self, risk_reward_ratio=self.risk_reward_ratio, atr_multiplier=self.atr_multiplier,atr_period=self.atr_period) 
        #self.trade_management_strategy = Swing_High_Low(self, swing_length=self.swing_length, risk_reward_ratio=self.risk_reward_ratio)
        self.risk_management_strategy = EfficiencyRatio(self, initial_risk_per_trade=self.initial_risk_per_trade, profit_risk_percentage=self.profit_risk_percentage)
        self.level_distribution_model = TradeLevelsCalculator(self, n_tp_levels=self.n_tp_levels, n_sl_levels=self.n_sl_levels)
        self.weight_distribution_model = EqualWeightedDistribution(self, n_tp_levels=self.n_tp_levels, n_sl_levels=self.n_sl_levels)
        self.trade_manager = TradeManager(
            trade_management_strategy=self.trade_management_strategy,
            level_distribution_model=self.level_distribution_model,
            weight_distribution_model=self.weight_distribution_model,
            n_tp_levels=self.n_tp_levels,
            n_sl_levels=self.n_sl_levels )
        self.num_trades=0



    def next(self):
        super().next()
        
        #if(self.num_trades < 1):

        if self.data.Close[-1] < self.bb_lower[-1]: 
            if self.position().is_short:
                self.position().close()  
            if not self.position():  
                self.add_buy_trade()
                #self.num_trades+=1
            
        elif self.data.Close[-1] > self.bb_upper[-1]:  
            if self.position().is_long:
                self.position().close()  
            if not self.position():  
                self.add_sell_trade()
                #self.num_trades+=1



if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)

    # Run the backtest
    bt = Backtest(GOOG, BollingerBandsMeanReversion, cash=100000, commission=0.002, margin=0.0001)
    stats = bt.run()
    bt.plot()
    print(stats)
    print(stats['_trades'])
    pd.DataFrame(stats['_trades']).to_csv("trades22.csv")
    bt.tear_sheet()