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
from TradeMaster.trade_management.trade_manager import TradeManager
from TradeMaster.trade_management.tp_sl.atr_tm import Single_tp_sl
from TradeMaster.trade_management.level_distribution.new_atr_tp_sl import TradeLevelsCalculator
from TradeMaster.trade_management.weight_distribution.atr_equal_weight import EqualWeightedDistribution

# Trade Configuration
class TradeConfiguration:
    """Modular configuration for trade components"""
    single_tp_sl_class = Single_tp_sl
    single_tp_sl_atr_multiplier = 3
    single_tp_sl_atr_period = 14
    single_tp_sl_risk_reward_ratio = 2
    
    risk_management_class = RiskPerTrade
    risk_management_initial_risk_per_trade = 0.1  # Matches initial_risk_per_trade from original
    risk_management_profit_risk_percentage = 0.1
    
    level_distribution_class = TradeLevelsCalculator
    n_tp_levels = 4  # 4 TP levels
    n_sl_levels = 4  # 3 SL levels
    
    weight_distribution_class = EqualWeightedDistribution
    weight_distribution_n_tp_levels = 4
    weight_distribution_n_sl_levels = 4

class AdxTrendStrategy(Strategy):
    adx_period = 14
    atr_period = 14
    position_splits = [0.33, 0.33, 0.34]  # Position splits for TP levels

    def init(self):
        # ADX Indicator
        self.adx = self.I(lambda: self.data.df.ta.adx(self.adx_period)[f"ADX_{self.adx_period}"].values)

        # Risk Management
        self.risk_management_strategy = TradeConfiguration.risk_management_class(
            self,
            initial_risk_per_trade=TradeConfiguration.risk_management_initial_risk_per_trade,
            profit_risk_percentage=TradeConfiguration.risk_management_profit_risk_percentage
        )
        
        # Trade Manager with separate TP and SL levels
        self.trade_manager = TradeManager(
            single_tp_sl_model=TradeConfiguration.single_tp_sl_class(
                self,
                atr_multiplier=TradeConfiguration.single_tp_sl_atr_multiplier,
                atr_period=TradeConfiguration.single_tp_sl_atr_period,
                risk_reward_ratio=TradeConfiguration.single_tp_sl_risk_reward_ratio
            ),
            level_distribution_model=TradeConfiguration.level_distribution_class(
                self,
                n_tp_levels=TradeConfiguration.n_tp_levels,
                n_sl_levels=TradeConfiguration.n_sl_levels
            ),
            weight_distribution_model=TradeConfiguration.weight_distribution_class(
                self,
                n_tp_levels=TradeConfiguration.weight_distribution_n_tp_levels,
                n_sl_levels=TradeConfiguration.weight_distribution_n_sl_levels
            ),
            n_tp_levels=TradeConfiguration.n_tp_levels,
            n_sl_levels=TradeConfiguration.n_sl_levels
        )
        
        self.total_trades = len(self.closed_trades)
        self.active_trades = {}
        self.trade_counter = 0
        self.trade_details = {}

    def next(self):
        self.on_trade_close()
        
        if len(self.data.Close) < self.adx_period:
            return

        if self.adx[-1] > 25:
            if self.data.Close[-1] > self.data.Close[-2]:  # Bullish trend
                if self.position().is_short:
                    self.position().close()
                if not self.position():
                    self.add_buy_trade()
            elif self.data.Close[-1] < self.data.Close[-2]:  # Bearish trend
                if self.position().is_long:
                    self.position().close()
                if not self.position():
                    self.add_sell_trade()

        current_price = self.data.Close[-1]
        trades_to_close = []

        for trade_id, trade_info in list(self.active_trades.items()):
            sl_levels = trade_info['sl_levels']
            tp_levels = trade_info['tp_levels']
            remaining_size = trade_info['remaining_size']
            original_size = trade_info['original_size']

            furthest_sl = min([list(sl.keys())[0] for sl in sl_levels])
            if trade_info['direction'] == 'buy' and current_price <= furthest_sl:
                self.sell(size=remaining_size)
                self.trade_details[trade_id]['booked'].append({'price': current_price, 'size': remaining_size, 'type': 'SL'})
                trades_to_close.append(trade_id)
                print(f"Trade {trade_id} closed at SL: {current_price}")
                continue
            elif trade_info['direction'] == 'sell' and current_price >= furthest_sl:
                self.buy(size=remaining_size)  # Cover short position
                self.trade_details[trade_id]['booked'].append({'price': current_price, 'size': remaining_size, 'type': 'SL'})
                trades_to_close.append(trade_id)
                print(f"Trade {trade_id} closed at SL: {current_price}")
                continue

            for i, tp_dict in enumerate(tp_levels):
                tp_level = list(tp_dict.keys())[0]
                weight = list(tp_dict.values())[0]
                if (trade_info['direction'] == 'buy' and current_price >= tp_level and weight > 0 and remaining_size > 0) or \
                   (trade_info['direction'] == 'sell' and current_price <= tp_level and weight > 0 and remaining_size > 0):
                    close_size = int(original_size * weight)
                    if close_size > remaining_size:
                        close_size = remaining_size
                    if close_size > 0:
                        if trade_info['direction'] == 'buy':
                            self.sell(size=close_size)
                        else:
                            self.buy(size=close_size)  # Cover short position
                        self.trade_details[trade_id]['booked'].append({'price': current_price, 'size': close_size, 'type': 'TP'})
                        trade_info['remaining_size'] -= close_size
                        tp_levels[i] = {tp_level: 0}
                        print(f"Trade {trade_id} closed {close_size} units at TP: {tp_level}")

            if trade_info['remaining_size'] <= 0:
                trades_to_close.append(trade_id)

        for trade_id in trades_to_close:
            del self.active_trades[trade_id]

    def add_buy_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        
        if risk_per_trade > 0:
            weighted_sl, weighted_tp = self.trade_manager.calculate_weighted_tp_sl_levels("buy")
            
            sl_levels = [list(sl.keys())[0] for sl in weighted_sl]
            furthest_sl = min(sl_levels)
            stop_loss_perc = abs(entry - furthest_sl) / entry
            trade_size = risk_per_trade / stop_loss_perc
            total_qty = math.ceil(trade_size / entry)
            
            trade_id = self.trade_counter
            self.active_trades[trade_id] = {
                'sl_levels': weighted_sl,
                'tp_levels': weighted_tp,
                'remaining_size': total_qty,
                'original_size': total_qty,
                'direction': 'buy'
            }
            self.trade_details[trade_id] = {
                'entry_price': entry,
                'sl_levels': weighted_sl,
                'tp_levels': weighted_tp,
                'booked': []
            }
            self.trade_counter += 1
            
            print(f"New Buy Trade - Entry: {entry:.2f}, SL Levels: {weighted_sl}, TP Levels: {weighted_tp}")
            self.buy(size=total_qty)

    def add_sell_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        
        if risk_per_trade > 0:
            weighted_sl, weighted_tp = self.trade_manager.calculate_weighted_tp_sl_levels("sell")
            
            sl_levels = [list(sl.keys())[0] for sl in weighted_sl]
            furthest_sl = max(sl_levels)  # For sell, SL is above entry
            stop_loss_perc = abs(furthest_sl - entry) / entry
            trade_size = risk_per_trade / stop_loss_perc
            total_qty = math.ceil(trade_size / entry)
            
            trade_id = self.trade_counter
            self.active_trades[trade_id] = {
                'sl_levels': weighted_sl,
                'tp_levels': weighted_tp,
                'remaining_size': total_qty,
                'original_size': total_qty,
                'direction': 'sell'
            }
            self.trade_details[trade_id] = {
                'entry_price': entry,
                'sl_levels': weighted_sl,
                'tp_levels': weighted_tp,
                'booked': []
            }
            self.trade_counter += 1
            
            print(f"New Sell Trade - Entry: {entry:.2f}, SL Levels: {weighted_sl}, TP Levels: {weighted_tp}")
            self.sell(size=total_qty)

    def on_trade_close(self):
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
    
    bt = Backtest(GOOG, AdxTrendStrategy, cash=1_000_000, commission=0.002, margin=0.000000000001)
    stats = bt.run()
    
    bt.plot()
    print(stats)
    print(stats['_trades'])