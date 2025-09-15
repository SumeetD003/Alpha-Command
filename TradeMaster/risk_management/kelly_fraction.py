import numpy as np

class KellyRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade, current_amount):
        """
        Initialize the KellyRiskManagement class.

        :param strategy: Strategy object, used for accessing trade history.
        :param initial_risk_per_trade: float, the fraction of capital to risk per trade.
        :param current_amount: float, the current capital amount.
        """
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        self.current_amount = current_amount

    def get_risk_per_trade(self):
        """
        Calculate the risk per trade based on the Kelly formula using the trade history.

        :return: float, risk per trade.
        """
        # Retrieve trade history from the strategy
        trades = self.strategy.get_trade_history()[-50:]  # Last 50 trades
        if not trades:  # Handle empty trade history
            print("No trade history available. Returning risk per trade as 0.")
            return 0

        # Calculate rolling statistics
        wins = [trade for trade in trades if trade > 0]
        losses = [trade for trade in trades if trade <= 0]

        W = len(wins) / len(trades) if trades else 0  # Win ratio
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0

        # Avoid division by zero
        if avg_loss == 0:
            print("Average loss is zero. Risk per trade cannot be calculated.")
            return 0

        R = avg_win / avg_loss  # Win/loss ratio

        # Calculate Kelly fraction
        kelly_fraction = W - (1 - W) / max(R, 0.001)  # Avoid division by zero in denominator
        kelly_fraction /= 3  # Take 1/3 of Kelly fraction
        kelly_fraction = min(kelly_fraction, 2)  # Cap at 2
        kelly_fraction = max(kelly_fraction, 0)  # Ensure non-negative

        # Calculate risk per trade
        risk_per_trade = kelly_fraction * self.initial_risk_per_trade * self.current_amount
        return risk_per_trade
