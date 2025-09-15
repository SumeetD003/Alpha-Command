import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

import pandas as pd
from decimal import Decimal
import seaborn as sns
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.risk_management.rpt import RiskPerTrade
from TradeMaster.risk_management.vps import VolatilityBasedPositionSizing
from TradeMaster.trade_management.tp_sl.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.tp_sl.std_dev import StandardDeviation_RR_TradeManagement
from TradeMaster.trade_management.tp_sl.Don_Chian_tm import DonchianChannelATRTradeManagement


def get_model_dictionaries():
    """
    Function to return dictionaries for risk management and trade management models.
    
    Returns:
        dict: A dictionary containing risk management models.
        dict: A dictionary containing trade management models.
    """
    # Risk Management Models Dictionary
    risk_models = {
        "Equal Risk Management": EqualRiskManagement,
        "Risk Per Trade": RiskPerTrade,
        "Volatility Based Position Sizing": VolatilityBasedPositionSizing,
    }

    # Trade Management Models Dictionary
    trade_models = {
        "ATR Trade Management": ATR_RR_TradeManagement,
        "Standard Deviation Trade Management": StandardDeviation_RR_TradeManagement,
        "Don Chian Trade Management": DonchianChannelATRTradeManagement,
    }

    return risk_models, trade_models


def generate_range(start, stop, step):
    """Generate a range of numbers with given start, stop, and step."""
    if isinstance(start, int) and isinstance(stop, int) and isinstance(step, int):
        return list(range(start, stop, step))
    else:
        start = Decimal(start)
        stop = Decimal(stop)
        step = Decimal(step)
        num_steps = int((stop - start) / step) + 1
        return [start + step * i for i in range(num_steps)]


def generate_heatmap(heatmap):
    """Generate and display a heatmap."""
    heatmap
    heatmap.sort_values().iloc[-3:]
    hm = heatmap.groupby(['n1', 'n2']).mean().unstack()
    sns.heatmap(hm[::-1], cmap='viridis')


def combine_dataframes(**kwargs):
    """
    Combine multiple DataFrames into one MultiIndex DataFrame.
    """
    combined_df = pd.concat(kwargs.values(), axis=1, keys=kwargs.keys())
    combined_df.ffill(inplace=True)  
    return combined_df
