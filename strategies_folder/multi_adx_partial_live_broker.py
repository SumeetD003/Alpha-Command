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
from TradeMaster.risk_management.efficiency_ratio_rm import EfficiencyRatio
from TradeMaster.trade_management.tp_sl.swing_high_low_tm import Swing_High_Low
from TradeMaster.trade_management.trade_manager import TradeManager
from TradeMaster.trade_management.weight_distribution.atr_equal_weight import EqualWeightedDistribution
from TradeMaster.risk_engine.Multi_Risk_Engine import BaseTradeStrategy, MultiTPSLStrategy,TrailingSLStrategy
from synapse import BrokerAggregator
from synapse.forwardtest import ForwardTest


class AdxTrendStrategy(TrailingSLStrategy):  
    adx_period = 14
    initial_risk_per_trade = 0.01
    profit_risk_percentage = 0.01
    atr_period = 14
    atr_multiplier = 3
    swing_length = 6
    risk_reward_ratio = 1.5
    n_tp_levels = 4
    n_sl_levels = 4
    
    def init(self):
        
        self.adx = self.I(self.data.df.ta.adx(self.adx_period)[f"ADX_{self.adx_period}"])
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
        self.num_trades = 0

    def next(self):
        super().next()  

        #if self.num_trades < 10:  
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
    aggregator = BrokerAggregator()
    aggregator.set_active_broker(
        'mt5', account_id=10005251219, password='-qUy3jYc', server='MetaQuotes-Demo',
        path="C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    )
    start_time = datetime.now(timezone.utc) 
    end_time = datetime.now(timezone.utc) + timedelta(days=30)


    ft = ForwardTest(AdxTrendStrategy, symbol='EURUSD', delta=timedelta(days=30), 
                    broker_aggregator=aggregator, timeframe='1m')
    stats = ft.run_live()
    # stats = ft.resume_bot(bot_id = 20)
    print(stats)