import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.helpers.functions import combine_dataframes
import yfinance as yf

GOOG = yf.download("GOOG", start="2023-01-01", end="2024-10-05")
AAPL = yf.download("AAPL", start="2023-01-01", end="2024-10-05")

df=combine_dataframes(GOOG=GOOG,AAPL=AAPL)
print(df)



class MyStrategy(Strategy):

    lookback = 10

    def init(self):
        self.roc = self.I(self.data.ta.roc(self.lookback), name='ROC')     #1

    def next(self):
        self.alloc.assume_zero()                                #2
        roc = self.roc.df.iloc[-1]                              #3
        (self.alloc.bucket['equity']                            #4
            .weight_explicitly(1/2)                             #7
            .apply())                                           #8
        self.rebalance(cash_reserve=0.01)   

bt = Backtest(df, MyStrategy, cash=100000, commission=.002)
stats = bt.run()
bt.plot()
print(stats)