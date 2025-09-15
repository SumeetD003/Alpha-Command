class Pivots_Points_TradeManagement:
    def __init__(self, strategy):
        """
        Initialize pivot-based trade management system.
        
        :param strategy: Reference to Strategy class object
        """
        self.strategy = strategy

    def calculate_tp_sl(self, direction):
        """
        Calculate stop loss and take profit levels based on pivot points.
        
        :param direction: Trade direction ('buy' or 'sell')
        :return: Tuple (stop_loss, take_profit)
        """
        df = self.strategy.data.df
        
        # Get previous period's prices
        prev_high = df['High'].iloc[-1]
        prev_low = df['Low'].iloc[-1]
        prev_close = df['Close'].iloc[-1]
        
        # Calculate pivot points
        pp = (prev_high + prev_low + prev_close) / 3
        r1 = (2 * pp) - prev_low
        r2 = pp + (prev_high - prev_low)
        s1 = (2 * pp) - prev_high
        s2 = pp - (prev_high - prev_low)
        rmean = (r1+r2) / 2
        smean = (s1+s2) / 2

        if direction.lower() == 'buy':
            stop_loss = smean 
            take_profit = rmean 
            current_price = df['Close'].iloc[-1]  
            if stop_loss >= current_price or take_profit <= current_price:
                raise ValueError(f"Invalid levels for buy order: SL ({stop_loss}) < Current Price ({current_price}) < TP ({take_profit})")
        elif direction.lower() == 'sell':
            stop_loss = rmean 
            take_profit = smean 
            current_price = df['Close'].iloc[-1] 
            if stop_loss <= current_price or take_profit >= current_price:
                raise ValueError(f"Invalid levels for sell order: SL ({stop_loss}) > Current Price ({current_price}) > TP ({take_profit})")
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy' or 'sell'.")
        
        
        stop_loss = round(stop_loss, 5)
        take_profit = round(take_profit, 5)

        return stop_loss, take_profit