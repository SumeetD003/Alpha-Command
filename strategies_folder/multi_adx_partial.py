import os
import sys
import math
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import pandas as pd
import warnings
import pandas_ta as ta
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import GOOG
from TradeMaster.risk_engine.Multi_Risk_Engine import BaseTradeStrategy, MultiTpSlModel, TrailingSlModel
from TradeMaster.trade_management.trade_manager import TradeManager
from TradeMaster.risk_management.efficiency_ratio_rm import EfficiencyRatio
from TradeMaster.trade_management.level_distribution.new_atr_tp_sl import TradeLevelsCalculator
from TradeMaster.trade_management.weight_distribution.atr_equal_weight import EqualWeightedDistribution
from TradeMaster.trade_management.tp_sl.swing_high_low_tm import Swing_High_Low
from TradeMaster.trade_management.trailing_based.std_dev_trailing_sl import StdDevTrailingStrategy  # Import StdDevTrailingStrategy

class AdxTrendStrategy(BaseTradeStrategy):
    adx_period = 14
    initial_risk_per_trade = 0.01
    profit_risk_percentage = 0.01
    atr_period = 14
    atr_multiplier = 3
    swing_length = 6
    risk_reward_ratio = 2000
    n_tp_levels = 4
    n_sl_levels = 4
    std_dev_multiplier = 1.5  
    std_dev_period = 16     

    def init(self):
        super().init()
        self.adx = self.I(self.data.df.ta.adx(self.adx_period)[f"ADX_{self.adx_period}"])

        # Initialize trade management components
        self.trade_management_strategy = Swing_High_Low(self, swing_length=self.swing_length, risk_reward_ratio=self.risk_reward_ratio)
        self.risk_management_strategy = EfficiencyRatio(self, initial_risk_per_trade=self.initial_risk_per_trade, profit_risk_percentage=self.profit_risk_percentage)
        self.level_distribution_model = TradeLevelsCalculator(self, n_tp_levels=self.n_tp_levels, n_sl_levels=self.n_sl_levels)
        self.weight_distribution_model = EqualWeightedDistribution(self, n_tp_levels=self.n_tp_levels, n_sl_levels=self.n_sl_levels)
        self.trade_manager = TradeManager(
            trade_management_strategy=self.trade_management_strategy,
            level_distribution_model=self.level_distribution_model,
            weight_distribution_model=self.weight_distribution_model,
            n_tp_levels=self.n_tp_levels,
            n_sl_levels=self.n_sl_levels
        )


        self.multi_tp_sl_model = MultiTpSlModel(strategy=self)
        self.trailing_sl_model = TrailingSlModel(
            strategy=self,
            trailing_sl_strategy=StdDevTrailingStrategy(
                std_dev_multiplier=self.std_dev_multiplier,
                std_dev_period=self.std_dev_period
            )  
        )
        # self.breakeven_model = BreakevenModel(strategy=self)
        # self.multiple_entries_model = MultipleEntriesModel(strategy=self)

        # Initialize the trailing SL strategy with data
        self.trailing_sl_model.trailing_sl_strategy.data = self.data
        self.trailing_sl_model.trailing_sl_strategy.init()

        self.num_trades = 0


    def next(self):
        
        super().next()

        if(self.num_trades < 8):
            if self.adx[-1] > 25:
                if self.data.Close[-1] > self.data.Close[-2]:  
                    # if self.position().is_short:
                    #     self.position().close()  
                    if not self.position():  
                        self.add_buy_trade()
                        self.num_trades+=1
                elif self.data.Close[-1] < self.data.Close[-2]: 
                    # if self.position().is_long:
                    #     self.position().close()  
                    if not self.position():
                        self.add_sell_trade()
                        self.num_trades+=1

if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    bt = Backtest(GOOG, AdxTrendStrategy, cash=1000000, commission=0, margin=0.001)
    stats = bt.run()
    bt.plot()
    
    print(stats)
    print(stats['_trades'])
    pd.DataFrame(stats['_trades']).to_csv("trades9.csv")
    
    # print("Type of bt._strategy:", type(bt._strategy))
    # print("Type of bt.strategy:", type(bt._strategy) if hasattr(bt, 'strategy') else "bt.strategy not available")
    # print("Type of bt._results.strategy:", type(bt._results._strategy))
    
    try:
        strategy = bt._results._strategy
        print("Using bt._results.strategy")
    except AttributeError:
        strategy = bt._strategy
        print("Using bt._strategy")
    
    print("Strategy object:", strategy)
    print("Has tradebook attribute:", hasattr(strategy, 'tradebook'))
    
    strategy.export_tradebook("tradebook_adx_strategy32.csv")