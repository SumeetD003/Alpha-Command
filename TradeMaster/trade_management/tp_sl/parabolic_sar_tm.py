import pandas as pd
import pandas_ta as ta
from TradeMaster.test import GOOG
from TradeMaster.helpers.indicators import calculate_atr  # Import from helpers.indicators

class PSAR_TradeManagement:
    def __init__(self, strategy, af0=0.02, af=0.02, af_max=0.2, risk_reward_ratio=1.5):
        self.strategy = strategy
        self.af0 = af0
        self.af = af
        self.af_max = af_max
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_period = 14  

    def calculate_tp_sl(self, direction):
        df = self.strategy.data.df
        entry_price = df['Close'].iloc[-1]
        
        # Calculate PSAR using pandas_ta
        psar_df = df.ta.psar(af0=self.af0, af=self.af, max_af=self.af_max)
        df['psar'] = psar_df[f'PSARl_{self.af}_{self.af_max}'].combine_first(psar_df[f'PSARs_{self.af}_{self.af_max}'])
        
        # Get the latest PSAR value
        psar_value = df['psar'].iloc[-2] 

        if pd.isna(psar_value):
            raise ValueError("PSAR value is NaN, insufficient data.")
        
        atr = calculate_atr(df, self.atr_period)  

        if direction.lower() == 'buy':
            # Ensure stop-loss is always below entry price
            stop_loss = min(psar_value, entry_price - 1.5 * atr)
            stop_loss = min(stop_loss, entry_price - 0.01)  # Ensure SL is below entry
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.risk_reward_ratio)

            # Validate SL and TP positioning
            if stop_loss >= entry_price or take_profit <= entry_price:
                stop_loss = entry_price * 0.99  # Adjust SL slightly below entry
                take_profit = entry_price * 1.01  # Adjust TP slightly above entry

        elif direction.lower() == 'sell':
            # Ensure stop-loss is always above entry price
            stop_loss = max(psar_value, entry_price + 1.5 * atr)
            stop_loss = max(stop_loss, entry_price + 0.01)  # Ensure SL is above entry
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.risk_reward_ratio)

            # Validate SL and TP positioning
            if stop_loss <= entry_price or take_profit >= entry_price:
                stop_loss = entry_price * 1.01  # Adjust SL slightly above entry
                take_profit = entry_price * 0.99  # Adjust TP slightly below entry

        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy' or 'sell'.")

        return round(stop_loss, 5), round(take_profit, 5)

    
#df = pd.DataFrame(GOOG)

#class Strategy:
 #   def __init__(self, df):
        self.data = type('obj', (object,), {'df': df})

#trategy = Strategy(df)
#trade_management = PSAR_TradeManagement(strategy)

# Test 'buy' direction
#stop_loss, take_profit = trade_management.calculate_tp_sl('buy')
#print(f"BUY Trade - Stop Loss: {stop_loss}, Take Profit: {take_profit}")

# Test 'sell' direction
#stop_loss, take_profit = trade_management.calculate_tp_sl('sell')
#print(f"SELL Trade - Stop Loss: {stop_loss}, Take Profit: {take_profit}")
