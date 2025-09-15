import os 
import sys
from TradeMaster.helpers.indicators import calculate_standard_deviation  # Import the function
import numpy as np
import pandas as pd
from typing import List

class StdDevTrailingStrategy:
    def __init__(self, std_dev_multiplier=1.5, std_dev_period=16):
        """
        Initialize the StdDevTrailingStrategy with parameters.

        Args:
            std_dev_multiplier: Multiplier for standard deviation to set trailing SL distance
            std_dev_period: Lookback period for calculating rolling standard deviation
        """
        self.std_dev_multiplier = std_dev_multiplier
        self.std_dev_period = std_dev_period
        self.std_dev = None
        self.trailing_sl_levels = []
        self.data = None  # Will be set by the strategy when used

    def init(self):
        """Initialize the trailing SL strategy."""
        self.set_std_dev()

    def set_std_dev(self):
        """
        Calculate the standard deviation of closing prices over the specified period
        using the imported calculate_standard_deviation function.
        """
        if self.data is None:
            raise ValueError("Data must be set before calculating standard deviation")
        
        # Use the imported function to calculate std dev for the entire series
        close_prices = pd.Series(self.data.Close)
        rolling_std = close_prices.rolling(window=self.std_dev_period).apply(
            lambda x: calculate_standard_deviation(pd.DataFrame({'Close': x}), self.std_dev_period),
            raw=False
        ).bfill()
        self.std_dev = rolling_std.values

    def set_trailing_sl(self, std_dev_multiplier: float = 1.5):
        """
        Set the multiplier for the trailing stop-loss based on standard deviation.
        """
        self.std_dev_multiplier = std_dev_multiplier

    def calculate_new_sl_levels(self, trade_id, trade_info, current_price, trail_price):
        """
        Calculate new trailing SL levels based on standard deviation.
        """
        index = len(self.data) - 1
        std_dev_value = self.std_dev[index] if index >= self.std_dev_period - 1 else np.nan
        if pd.isna(std_dev_value):
            std_dev_value = 0.1  # Fallback value

        is_long = trade_info['is_long']
        current_sl_levels = [float(next(iter(sl))) for sl in trade_info['sl_levels']] if trade_info['sl_levels'] else []
        trailing_sl = max(current_sl_levels) if is_long and current_sl_levels else min(current_sl_levels) if current_sl_levels else (current_price if is_long else trail_price)

        if is_long:
            new_sl = current_price - std_dev_value * self.std_dev_multiplier
            new_trailing_sl = max(trailing_sl, new_sl)
        else:
            new_sl = current_price + std_dev_value * self.std_dev_multiplier
            new_trailing_sl = min(trailing_sl, new_sl)

        # Return a list of new SL levels, preserving the original number of levels
        new_sl_levels = [new_trailing_sl if i == 0 else sl for i, sl in enumerate(current_sl_levels)]
        self.trailing_sl_levels.append(round(new_trailing_sl, 5))
        return new_sl_levels

    def get_sl_levels(self) -> List[float]:
        """
        Return the historical trailing stop-loss levels.
        """
        return self.trailing_sl_levels