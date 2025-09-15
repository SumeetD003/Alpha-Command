import os
import sys
import warnings
import math

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from TradeMaster.backtesting import Backtest
from TradeMaster.test import GOOG
from TradeMaster.risk_engine.Multi_Risk_Engine import MultiRiskEngine  
from TradeMaster.trade_management.tp_sl.swing_high_low_tm import Swing_High_Low
from TradeMaster.risk_management.efficiency_ratio_rm import EfficiencyRatio
from TradeMaster.trade_management.weight_distribution.swing_equal_weight import EqualWeightedDistribution
from TradeMaster.trade_management.trade_manager import TradeManager
from TradeMaster.trade_management.level_distribution.swing_atr_multi_tp_sl import TradeLevelsCalculator  

class AdxTrendStrategy(MultiRiskEngine):
    adx_period = 14
    n_tp_levels = 4
    n_sl_levels = 4
    initial_risk_per_trade = 0.01
    profit_risk_percentage = 0.01
    atr_period = 14
    atr_multiplier = 3
    swing_length = 6
    risk_reward_ratio = 2

    def __init__(self, broker, data, params, *args, **kwargs):
        super().__init__(broker, data, params, *args, **kwargs)
        
        self.n_tp_levels = params.get('n_tp_levels', self.n_tp_levels)
        self.n_sl_levels = params.get('n_sl_levels', self.n_sl_levels)
        self.initial_risk_per_trade = params.get('initial_risk_per_trade', self.initial_risk_per_trade)
        self.profit_risk_percentage = params.get('profit_risk_percentage', self.profit_risk_percentage)
        self.swing_length = params.get('swing_length', self.swing_length)
        self.atr_period = params.get('atr_period', self.atr_period)
        self.atr_multiplier = params.get('atr_multiplier', self.atr_multiplier)
        self.risk_reward_ratio = params.get('risk_reward_ratio', self.risk_reward_ratio)
        
        self.level_distribution_model = TradeLevelsCalculator(self, n_tp_levels=self.n_tp_levels, n_sl_levels=self.n_sl_levels)
        self.weight_distribution_model = EqualWeightedDistribution(self, n_tp_levels=self.n_tp_levels, n_sl_levels=self.n_sl_levels)
        
       
        
        self.active_trades = {}
        self.total_trades = len(self.closed_trades)

    def init(self):
        super().init()
        self.adx = self.I(self.data.df.ta.adx(self.adx_period)[f"ADX_{self.adx_period}"])
        self.trade_management_strategy = Swing_High_Low(self, swing_length=self.swing_length, risk_reward_ratio=self.risk_reward_ratio)  # Explicitly set Swing_High_Low
        self.risk_management_strategy = EfficiencyRatio(self, initial_risk_per_trade=self.initial_risk_per_trade, profit_risk_percentage=self.profit_risk_percentage)
        self.trade_manager = TradeManager(
            trade_management_strategy=self.trade_management_strategy,  
            level_distribution_model=self.level_distribution_model,
            weight_distribution_model=self.weight_distribution_model,
            n_tp_levels=self.n_tp_levels,
            n_sl_levels=self.n_sl_levels
        )
    def next(self):
        self.on_trade_close()
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
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    bt = Backtest(GOOG, AdxTrendStrategy, cash=100000000000, commission=0.001, margin=0.00001)
    stats = bt.run()
    bt.plot()
    
    print(stats)
    print(stats['_trades'])
    
    print("Type of bt._strategy:", type(bt._strategy))
    print("Type of bt._results.strategy:", type(bt._results._strategy))
    
    try:
        strategy = bt._results._strategy 
        print("Using bt._results.strategy")
    except AttributeError:
        strategy = bt._strategy  
        print("Using bt._strategy")
    
    print("Strategy object:", strategy)
    print("Has tradebook attribute:", hasattr(strategy, 'tradebook'))
    
    strategy.export_tradebook("tradebook_adx_strategy1.csv")