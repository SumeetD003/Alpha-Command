import numpy as np
from hmmlearn import hmm

class HMMRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, n_components=2, n_iter=100):
        '''
        Initializes the HMM-based risk management strategy.
        
        Parameters:
        - strategy: Reference to the strategy object.
        - initial_risk_per_trade: Default risk per trade (e.g., 1% of account equity).
        - n_components: Number of hidden states in the HMM (e.g., 2 for high/low volatility).
        - n_iter: Number of iterations for HMM training.
        '''
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        self.n_components = n_components
        self.n_iter = n_iter
        self.hmm_model = hmm.GaussianHMM(n_components=n_components, n_iter=n_iter)
        self.current_state = None
        self.returns_history = [] 

    def get_risk_per_trade(self):
        '''
        Calculates the risk per trade based on the current market state predicted by the HMM.
        '''
        # Calculate returns from the strategy's historical data
        prices = self.strategy.data.Close  # Assuming 'close' prices are available
        returns = np.diff(prices) / prices[:-1]  # Simple percentage returns
        self.returns_history.extend(returns)

        # Train HMM if enough data is available
        if len(self.returns_history) >= 10:
            returns_array = np.array(self.returns_history).reshape(-1, 1)
            self.hmm_model.fit(returns_array)

            # Predict the current market state
            latest_return = np.array(self.returns_history[-1]).reshape(-1, 1)
            self.current_state = self.hmm_model.predict(latest_return)[0]

        # Adjust risk based on the predicted market state
        if self.current_state == 0:  # Low volatility state
            risk_multiplier = 1.0  # Use default risk
        elif self.current_state == 1:  # High volatility state
            risk_multiplier = 0.5  # Reduce risk by half
        else:
            risk_multiplier = 1.0  # Fallback to default risk

        trade_size = self.strategy._broker._cash * self.initial_risk_per_trade * risk_multiplier
        return trade_size

    def update_after_loss(self):
        '''
        Updates the state after a loss.
        '''
        self.current_state = None  # Reset state (optional, can be customized)

    def update_after_win(self):
        '''
        Updates the state after a win.
        '''
        self.current_state = None  # Reset state (optional, can be customized)