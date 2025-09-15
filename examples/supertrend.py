import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import math
import pandas_ta as ta
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import GOOG  # Importing the Google dataset
from TradeMaster.trade_management.single_tp_sl.atr_tm import ATR_RR_TradeManagement
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.risk_management.rpt import RiskPerTrade


class SupertrendStrategy(Strategy):
    initial_risk_per_trade = 0.01
    risk_reward_ratio = 1.5
    atr_multiplier = 3.0  # Default value
    atr_period = 14       # Default value
    initial_equity = 100000  # Default value for equity
    
    def init(self):
        self.total_trades = len(self.closed_trades)
        self.trade_management_strategy = ATR_RR_TradeManagement(self, risk_reward_ratio=self.risk_reward_ratio, atr_multiplier=self.atr_multiplier, atr_period=self.atr_period)
        self.risk_management_strategy = RiskPerTrade(self,initial_risk_per_trade = self.initial_risk_per_trade, profit_risk_percentage = 0.02)
    

    def next(self):
        self.on_trade_close()
        current_signal = self.data.signal[-1]
        current_signaldirection = self.data.signal_direction[-1]

        if current_signal == 1:
            if not self.position():
                self.add_buy_trade()
            elif self.position().is_short:
                self.position().close()
                self.add_buy_trade()

        if current_signal == -1:
            if not self.position():
                self.add_sell_trade()
            elif self.position().is_long:
                self.position().close()
                self.add_sell_trade()

        if current_signaldirection < 0 and self.position().is_short:
            self.position().close()

        if current_signaldirection > 0 and self.position().is_long:
            self.position().close()

    def add_buy_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        print(f"Close price: {self.data.Close[-1]}")

        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(direction="buy")
            stop_loss_perc = (entry - stop_loss) / entry
            trade_size = risk_per_trade / stop_loss_perc
            #qty = math.ceil(trade_size / self.data.Close[-1])
            print(f"Risk per trade: {risk_per_trade}")
            print(f"Entry price: {entry}")
            print(f"Stop loss: {stop_loss}, Take profit: {take_profit}")
            stop_loss_perc = (entry - stop_loss) / entry
            print(f"Stop loss percentage: {stop_loss_perc}")
            trade_size = risk_per_trade / stop_loss_perc
            print(f"Calculated trade size: {trade_size}")


            # Check if there's enough liquidity to place the trade
            #if qty * entry <= self._broker._cash:
                #self.buy(size=qty, sl=stop_loss, tp=take_profit)
            #else:
                #print(f"Insufficient liquidity to buy: Available cash = {self._broker._cash}, Required cash = {qty * entry}")

    def add_sell_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(direction="sell")
            stop_loss_perc = (stop_loss - entry) / entry
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])

            # Check if there's enough liquidity to place the trade
            if qty * entry <= self._broker._cash:
                self.sell(size=qty, sl=stop_loss, tp=take_profit)
            else:
                print(f"Insufficient liquidity to sell: Available cash = {self._broker._cash}, Required cash = {qty * entry}")

    def on_trade_close(self):
        num_of_trades_closed = len(self.closed_trades) - self.total_trades
        if num_of_trades_closed > 0:
            for trade in self.closed_trades[-num_of_trades_closed:]:
                if trade.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()
        self.total_trades = len(self.closed_trades)
        
        

if __name__ == '__main__':
    data = GOOG  # Using Google dataset directly from the TradeMaster test module
    bt = Backtest(data, SupertrendStrategy, cash=1000000, commission=0.002)
    stats = bt.run()
    print(stats)
    bt.plot()
