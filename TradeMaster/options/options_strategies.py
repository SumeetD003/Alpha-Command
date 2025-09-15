import os 
import pandas as pd
from glob import glob

from TradeMaster.options.options_datafetcher import OptionsDataFetcher

class OptionsStrategy:
    def __init__(self, combined_df):
        """
        Initialize with a combined DataFrame of options contracts.
        """
        self.selector = OptionsDataFetcher()

    # --- Bullish Strategies ---
    
    # Long Call
    def long_call(self, strike_price, expiry_date, ticker):
        call_option = self.selector.select_contracts(strike_price=strike_price, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if call_option.empty:
            raise ValueError("Call option not available for the given strike price and expiry date.")
        return call_option

    # Short Put
    def short_put(self, strike_price, expiry_date, ticker):
        put_option = self.selector.select_contracts(strike_price=strike_price, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if put_option.empty:
            raise ValueError("Put option not available for the given strike price and expiry date.")
        return put_option

    # Bull Call Spread
    def bull_call_spread(self, lower_strike, upper_strike, expiry_date, ticker):
        buy_call = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        sell_call = self.selector.select_contracts(strike_price=upper_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if buy_call.empty or sell_call.empty:
            raise ValueError("Options contracts not available for the given strike prices and expiry date.")
        return pd.concat([buy_call, sell_call])

    # Bull Put Spread
    def bull_put_spread(self, lower_strike, upper_strike, expiry_date, ticker):
        sell_put = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        buy_put = self.selector.select_contracts(strike_price=upper_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if sell_put.empty or buy_put.empty:
            raise ValueError("Options contracts not available for the given strike prices and expiry date.")
        return pd.concat([sell_put, buy_put])

    # Call Ratio Back Spread
    def call_ratio_back_spread(self, lower_strike, higher_strike, expiry_date, ticker):
        sell_call = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        buy_call = self.selector.select_contracts(strike_price=higher_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if sell_call.empty or buy_call.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([sell_call, buy_call])

    # Long Synthetic
    def long_synthetic(self, strike_price, expiry_date, ticker):
        long_call = self.long_call(strike_price, expiry_date, ticker)
        short_put = self.short_put(strike_price, expiry_date, ticker)
        return pd.concat([long_call, short_put])

    # Range Forward
    def range_forward(self, lower_strike, upper_strike, expiry_date, ticker):
        long_put = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        long_call = self.selector.select_contracts(strike_price=upper_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if long_put.empty or long_call.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([long_put, long_call])

    # Bullish Butterfly
    def bullish_butterfly(self, lower_strike, middle_strike, upper_strike, expiry_date, ticker):
        buy_lower_call = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        sell_middle_call = self.selector.select_contracts(strike_price=middle_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        buy_upper_call = self.selector.select_contracts(strike_price=upper_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if buy_lower_call.empty or sell_middle_call.empty or buy_upper_call.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([buy_lower_call, sell_middle_call, buy_upper_call])

    # Bullish Condor
    def bullish_condor(self, lower_put_strike, middle_put_strike, middle_call_strike, upper_call_strike, expiry_date, ticker):
        bull_put = self.bull_put_spread(lower_put_strike, middle_put_strike, expiry_date, ticker)
        bull_call = self.bull_call_spread(middle_call_strike, upper_call_strike, expiry_date, ticker)
        return pd.concat([bull_put, bull_call])

    # --- Bearish Strategies ---
    
    # Short Call
    def short_call(self, strike_price, expiry_date, ticker):
        call_option = self.selector.select_contracts(strike_price=strike_price, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if call_option.empty:
            raise ValueError("Call option not available for the given strike price and expiry date.")
        return call_option

    # Long Put
    def long_put(self, strike_price, expiry_date, ticker):
        put_option = self.selector.select_contracts(strike_price=strike_price, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if put_option.empty:
            raise ValueError("Put option not available for the given strike price and expiry date.")
        return put_option

    # Bear Call Spread
    def bear_call_spread(self, lower_strike, upper_strike, expiry_date, ticker):
        sell_call = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        buy_call = self.selector.select_contracts(strike_price=upper_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if sell_call.empty or buy_call.empty:
            raise ValueError("Options contracts not available for the given strike prices and expiry date.")
        return pd.concat([sell_call, buy_call])

    # Bear Put Spread
    def bear_put_spread(self, lower_strike, upper_strike, expiry_date, ticker):
        buy_put = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        sell_put = self.selector.select_contracts(strike_price=upper_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if buy_put.empty or sell_put.empty:
            raise ValueError("Options contracts not available for the given strike prices and expiry date.")
        return pd.concat([buy_put, sell_put])

    # Put Ratio Back Spread
    def put_ratio_back_spread(self, lower_strike, higher_strike, expiry_date, ticker):
        sell_put = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        buy_put = self.selector.select_contracts(strike_price=higher_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if sell_put.empty or buy_put.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([sell_put, buy_put])

    # Short Synthetic
    def short_synthetic(self, strike_price, expiry_date, ticker):
        short_call = self.short_call(strike_price, expiry_date, ticker)
        long_put = self.long_put(strike_price, expiry_date, ticker)
        return pd.concat([short_call, long_put])

    # Risk Reversal
    def risk_reversal(self, lower_put_strike, upper_call_strike, expiry_date, ticker):
        long_put = self.long_put(lower_put_strike, expiry_date, ticker)
        long_call = self.long_call(upper_call_strike, expiry_date, ticker)
        return pd.concat([long_put, long_call])

    # Bearish Butterfly
    def bearish_butterfly(self, lower_strike, middle_strike, upper_strike, expiry_date, ticker):
        buy_lower_put = self.selector.select_contracts(strike_price=lower_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        sell_middle_put = self.selector.select_contracts(strike_price=middle_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        buy_upper_put = self.selector.select_contracts(strike_price=upper_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if buy_lower_put.empty or sell_middle_put.empty or buy_upper_put.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([buy_lower_put, sell_middle_put, buy_upper_put])

    # Bearish Condor
    def bearish_condor(self, lower_call_strike, middle_call_strike, middle_put_strike, upper_put_strike, expiry_date, ticker):
        bear_call = self.bear_call_spread(lower_call_strike, middle_call_strike, expiry_date, ticker)
        bear_put = self.bear_put_spread(middle_put_strike, upper_put_strike, expiry_date, ticker)
        return pd.concat([bear_call, bear_put])

    # --- Bi-Directional Strategies ---
    
    # Long Straddle
    def long_straddle(self, strike_price, expiry_date, ticker):
        return self.long_strangle(strike_price, strike_price, expiry_date, ticker)

    # Short Straddle
    def short_straddle(self, strike_price, expiry_date, ticker):
        return self.short_strangle(strike_price, strike_price, expiry_date, ticker)

    # Long Strangle
    def long_strangle(self, call_strike, put_strike, expiry_date, ticker):
        call_option = self.selector.select_contracts(strike_price=call_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        put_option = self.selector.select_contracts(strike_price=put_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if call_option.empty or put_option.empty:
            raise ValueError("Options contracts not available for the given strike prices and expiry date.")
        return pd.concat([call_option, put_option])

    # Short Strangle
    def short_strangle(self, call_strike, put_strike, expiry_date, ticker):
        call_option = self.selector.select_contracts(strike_price=call_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        put_option = self.selector.select_contracts(strike_price=put_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if call_option.empty or put_option.empty:
            raise ValueError("Options contracts not available for the given strike prices and expiry date.")
        return pd.concat([call_option, put_option])

    # Jade Lizard
    def jade_lizard(self, call_strike, put_strike, expiry_date, ticker):
        short_put = self.selector.select_contracts(strike_price=put_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        short_call = self.selector.select_contracts(strike_price=call_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        if short_put.empty or short_call.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([short_put, short_call])

    # Reverse Jade Lizard
    def reverse_jade_lizard(self, call_strike, put_strike, expiry_date, ticker):
        long_call = self.selector.select_contracts(strike_price=call_strike, expiry_date=expiry_date, instrument_type='CE', ticker=ticker)
        short_put = self.selector.select_contracts(strike_price=put_strike, expiry_date=expiry_date, instrument_type='PE', ticker=ticker)
        if long_call.empty or short_put.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([long_call, short_put])

    # Call Ratio Spread
    def call_ratio_spread(self, lower_strike, higher_strike, expiry_date, ticker):
        return self.call_ratio_back_spread(lower_strike, higher_strike, expiry_date, ticker)

    # Put Ratio Spread
    def put_ratio_spread(self, lower_strike, higher_strike, expiry_date, ticker):
        return self.put_ratio_back_spread(lower_strike, higher_strike, expiry_date, ticker)

    # Batman Strategy
    def batman_strategy(self, call_strike, put_strike, expiry_date, ticker):
        return self.long_strangle(call_strike, put_strike, expiry_date, ticker)

    # Long Iron Fly
    def long_iron_fly(self, lower_strike, middle_strike, upper_strike, expiry_date, ticker):
        return self.bullish_butterfly(lower_strike, middle_strike, upper_strike, expiry_date, ticker)

    # Short Iron Fly
    def short_iron_fly(self, lower_strike, middle_strike, upper_strike, expiry_date, ticker):
        return self.bearish_butterfly(lower_strike, middle_strike, upper_strike, expiry_date, ticker)

    # Double Fly
    def double_fly(self, lower_call_strike, middle_call_strike, upper_call_strike, lower_put_strike, middle_put_strike, upper_put_strike, expiry_date, ticker):
        call_fly = self.bullish_butterfly(lower_call_strike, middle_call_strike, upper_call_strike, expiry_date, ticker)
        put_fly = self.bearish_butterfly(lower_put_strike, middle_put_strike, upper_put_strike, expiry_date, ticker)
        return pd.concat([call_fly, put_fly])

    # Long Iron Condor
    def long_iron_condor(self, lower_put_strike, upper_put_strike, lower_call_strike, upper_call_strike, expiry_date, ticker):
        return self.iron_condor(lower_put_strike, upper_put_strike, lower_call_strike, upper_call_strike, expiry_date, ticker)

    # Short Iron Condor
    def short_iron_condor(self, lower_put_strike, upper_put_strike, lower_call_strike, upper_call_strike, expiry_date, ticker):
        return self.iron_condor(lower_put_strike, upper_put_strike, lower_call_strike, upper_call_strike, expiry_date, ticker)

    # Double Condor
    def double_condor(self, lower_call_strike, middle_call_strike, upper_call_strike, lower_put_strike, middle_put_strike, upper_put_strike, expiry_date, ticker):
        bullish_condor = self.bullish_condor(lower_call_strike, middle_call_strike, upper_call_strike, expiry_date, ticker)
        bearish_condor = self.bearish_condor(lower_put_strike, middle_put_strike, upper_put_strike, expiry_date, ticker)
        return pd.concat([bullish_condor, bearish_condor])

    # --- Calendar Spreads and Diagonals ---

    # Call Calendar Spread
    def call_calendar(self, strike_price, short_expiry, long_expiry, ticker):
        short_term_call = self.selector.select_contracts(strike_price=strike_price, expiry_date=short_expiry, instrument_type='CE', ticker=ticker)
        long_term_call = self.selector.select_contracts(strike_price=strike_price, expiry_date=long_expiry, instrument_type='CE', ticker=ticker)
        if short_term_call.empty or long_term_call.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([short_term_call, long_term_call])

    # Put Calendar Spread
    def put_calendar(self, strike_price, short_expiry, long_expiry, ticker):
        short_term_put = self.selector.select_contracts(strike_price=strike_price, expiry_date=short_expiry, instrument_type='PE', ticker=ticker)
        long_term_put = self.selector.select_contracts(strike_price=strike_price, expiry_date=long_expiry, instrument_type='PE', ticker=ticker)
        if short_term_put.empty or long_term_put.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([short_term_put, long_term_put])

    # Diagonal Calendar Spread
    def diagonal_calendar(self, short_strike, long_strike, short_expiry, long_expiry, ticker):
        short_term_option = self.selector.select_contracts(strike_price=short_strike, expiry_date=short_expiry, instrument_type='CE', ticker=ticker)
        long_term_option = self.selector.select_contracts(strike_price=long_strike, expiry_date=long_expiry, instrument_type='CE', ticker=ticker)
        if short_term_option.empty or long_term_option.empty:
            raise ValueError("Options contracts not available.")
        return pd.concat([short_term_option, long_term_option])

    # Call Butterfly Spread
    def call_butterfly(self, lower_strike, middle_strike, upper_strike, expiry_date, ticker):
        return self.bullish_butterfly(lower_strike, middle_strike, upper_strike, expiry_date, ticker)

    # Put Butterfly Spread
    def put_butterfly(self, lower_strike, middle_strike, upper_strike, expiry_date, ticker):
        return self.bearish_butterfly(lower_strike, middle_strike, upper_strike, expiry_date, ticker)
