import math
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


from TradeMaster.lib import crossover
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.test import SMA
from TradeMaster.trade_management.single_tp_sl.atr_tm import ATR_RR_TradeManagement
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.helpers.functions import combine_dataframes
import yfinance as yf

GOOG = yf.download("GOOG", start="2023-01-01", end="2024-10-05")
AAPL = yf.download("AAPL", start="2023-01-01", end="2024-10-05")

df=combine_dataframes(GOOG=GOOG,AAPL=AAPL)



class SmaCross(Strategy):
    n1 = 20
    n2 = 50

    risk_reward_ratio=1.5
    atr_multiplier=3
    initial_risk_per_trade=0.01

    def init(self):
        self.sma1 = self.I(self.data.df.ta.sma(10))
        self.sma2 = self.I(self.data.df.ta.sma(30))
        self.trade_management_strategy = ATR_RR_TradeManagement(3,1.5)
        self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        self.total_trades=len(self.closed_trades)

    def next(self):
        self.on_trade_close()
        if self.data.Close[-1][0] > self.sma1[-1][0]:
            self.position(ticker='AAPL').close()
            risk_per_trade = self.risk_management_strategy.get_risk_per_trade(self._broker._cash)
            print(risk_per_trade)
            entry=self.data.Close[-1][0]
            if risk_per_trade > 0:
                stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(df=self.data.df["AAPL"],direction="buy")
                stop_loss_perc = (entry - stop_loss)/entry
                trade_size = risk_per_trade/stop_loss_perc
                qty = math.ceil(trade_size / self.data.Close[-1][0])
                print(qty)
                self.buy(ticker='AAPL', sl=stop_loss, tp=take_profit)
        if self.data.Close[-1][1] > self.sma1[-1][1]:
            self.position(ticker='GOOG').close()
            risk_per_trade = self.risk_management_strategy.get_risk_per_trade(self._broker._cash)
            print(risk_per_trade)
            entry=self.data.Close[-1][1]
            if risk_per_trade > 0:
                stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(df=self.data.df["GOOG"],direction="buy")
                stop_loss_perc = (stop_loss - entry)/entry
                trade_size = risk_per_trade/stop_loss_perc
                qty = math.ceil(trade_size / self.data.Close[-1][1])
                print(qty)
                self.buy(ticker='GOOG', sl=stop_loss, tp=take_profit)

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

bt = Backtest(df, SmaCross, cash=100000, commission=.002)
stats = bt.run()
bt.plot()
print(stats)
print(stats._trades)