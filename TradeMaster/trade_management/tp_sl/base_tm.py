from TradeMaster.helpers.indicators import calculate_atr

class Base_TM:
    def __init__(self, atr_multiplier, risk_to_reward_ratio):
        """
        Initialize the TradeManagement base class.

        :param atr_multiplier: float, the multiplier for ATR to set stop loss
        :param risk_to_reward_ratio: float, the desired risk-to-reward ratio
        """
        self.atr_multiplier = atr_multiplier
        self.risk_to_reward_ratio = risk_to_reward_ratio

