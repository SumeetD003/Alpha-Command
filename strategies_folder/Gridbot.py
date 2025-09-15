import math
import warnings
import pandas as pd
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import GOOG
import pandas_ta as ta

class GridTradingStrategy(Strategy):
    no_grids = 21
    capital_per_grid = 0.0005  
    lookback = 200
    units_per_grid = 10  
    def init(self):
        self.grids = []
        self.active_orders = {}  
        self.upper_limit = None
        self.lower_limit = None
        self.current_step = 0
        self.initial_position_taken = False  

    def create_grids(self):
        """Creates or updates grid levels dynamically based on price movement."""
        current_price = self.data.Close[-1]
        new_grid_created = False
        
        if not self.grids:
            if self.current_step < self.lookback - 1:
                data_slice = self.data.Close[:self.current_step + 1]
            else:
                data_slice = self.data.Close[self.current_step - (self.lookback - 1):self.current_step + 1]
            self.lower_limit = float(min(data_slice))
            
            self.upper_limit = current_price + (current_price - self.lower_limit)
            new_grid_created = True
        elif current_price < self.lower_limit:
            self.upper_limit = self.lower_limit 
            self.lower_limit = current_price     
            new_grid_created = True
        elif current_price > self.upper_limit:
            self.lower_limit = self.upper_limit  
            self.upper_limit = current_price     
            new_grid_created = True
        
        grid_range = self.upper_limit - self.lower_limit
        if grid_range == 0: 
            grid_interval = 0.1
        else:
            grid_interval = grid_range / (self.no_grids - 1) 
        
        self.grids = [self.lower_limit + i * grid_interval for i in range(self.no_grids)]
        
        print(f"Grid updated: Lower Limit={self.lower_limit:.2f}, Upper Limit={self.upper_limit:.2f}, "
              f"Levels={[round(g, 2) for g in self.grids]}")
        
        
        if new_grid_created:
            self.initial_position_taken = False  
            self.handle_initial_buy(current_price)

    def calculate_trade_size(self, grid_level):
        """Calculates trade size based on total equity for additional orders."""
        available_cash = self.equity 
        capital_allocation = available_cash * self.capital_per_grid
        trade_size = capital_allocation / grid_level
        return max(1, math.floor(trade_size))

    def handle_initial_buy(self, current_price):
        """Handles initial buy and sell limit orders when a new grid is created."""
        sell_levels = [g for g in self.grids if g > current_price]
        
        num_sell_levels = len(sell_levels)
        if num_sell_levels > 0 and not self.initial_position_taken:
            
            total_buy_size = num_sell_levels * self.units_per_grid
            print(f"Initial Buy: Current Price={current_price:.2f}, Sell Levels={num_sell_levels}, Total Buy Size={total_buy_size}")
            
            
            self.buy(size=total_buy_size)  
            
            
            sell_size_per_level = total_buy_size // num_sell_levels
            remaining_size = total_buy_size % num_sell_levels  
            
            for i, grid in enumerate(sell_levels):
                sell_size = sell_size_per_level + (1 if i < remaining_size else 0)  
                if sell_size > 0:
                    order = self.sell(size=sell_size, limit=grid)
                    self.active_orders[grid] = order
                    print(f"Placed Initial Sell Order: Grid={grid:.2f}, Size={sell_size}, Equity={self.equity:.2f}")
            
            self.initial_position_taken = True  

    def update_active_orders(self):
        """Places additional buy and sell limit orders based on current price."""
        current_price = self.data.Close[-1]
        
        for grid, order in list(self.active_orders.items()):
            if order in self.orders and grid < current_price:  
                order.cancel()
                self.active_orders.pop(grid)
        
        buy_levels = [g for g in self.grids if g < current_price]
        sell_levels = [g for g in self.grids if g > current_price and g not in self.active_orders]
        
        for grid in buy_levels:
            trade_size = self.calculate_trade_size(grid)
            cost = trade_size * grid 
            if trade_size > 0:
                order = self.buy(size=trade_size, limit=grid)
                self.active_orders[grid] = order
                print(f"Placed Buy Order: Grid={grid:.2f}, Size={trade_size}, Cost={cost:.2f}, Equity={self.equity:.2f}")
        
        for grid in sell_levels:
            trade_size = self.calculate_trade_size(grid)
            cost = trade_size * grid 
            if trade_size > 0:
                order = self.sell(size=trade_size, limit=grid)
                self.active_orders[grid] = order
                print(f"Placed Sell Order: Grid={grid:.2f}, Size={trade_size}, Cost={cost:.2f}, Equity={self.equity:.2f}")
        
        print(f"Active Orders: {[f'{round(k, 2)}: {v.__repr__()}' for k, v in self.active_orders.items()]}")

    def get_closest_grid_level_below(self, price):
        """Finds the closest grid level below the given price."""
        below = [g for g in self.grids if g < price]
        return max(below) if below else None

    def get_closest_grid_level_above(self, price):
        """Finds the closest grid level above the given price."""
        above = [g for g in self.grids if g > price]
        return min(above) if above else None

    def next(self):
        print("Current cash:", self._broker._cash)
        current_price = self.data.Close[-1]

        if self.current_step < self.lookback - 1:
            self.current_step += 1
            return
        
        if not self.grids or current_price < self.lower_limit or current_price > self.upper_limit:
            self.create_grids()  
        else:
            self.update_active_orders()

        current_bar = len(self.data.Close) - 1  
        for trade in self.trades():  
            if trade.exit_bar is not None and trade.exit_bar == current_bar:
                entry_price = trade.entry_price
                exit_price = trade.exit_price
                trade_size = abs(trade.size)
                
                if trade.is_long: 
                    self.active_orders.pop(entry_price, None)
                    new_sell_level = self.get_closest_grid_level_above(current_price)
                    print(f"--- Trade Closed (Long) ---")
                    print(f"Grid Levels: {[round(g, 2) for g in self.grids]}")
                    print(f"Entry Grid Level: {entry_price:.2f}")
                    print(f"Position Size: {trade_size}")
                    print(f"Exit Grid Level: {exit_price:.2f}")
                    print(f"Lower Limit: {self.lower_limit:.2f}, Upper Limit: {self.upper_limit:.2f}")
                    print(f"Profit/Loss: {trade.pl:.2f}")
                    print(f"Equity: {self.equity:.2f}")
                    print("---------------------")
                    
                    if new_sell_level and new_sell_level not in self.active_orders:
                        trade_size = self.calculate_trade_size(new_sell_level)
                        order = self.sell(size=trade_size, limit=new_sell_level)
                        self.active_orders[new_sell_level] = order
                        print(f"Buy filled and closed at {entry_price:.2f}, New Sell Order at {new_sell_level:.2f}")
                
                elif trade.is_short:  
                    self.active_orders.pop(entry_price, None)
                    new_buy_level = self.get_closest_grid_level_below(current_price)
                    print(f"--- Trade Closed (Short) ---")
                    print(f"Grid Levels: {[round(g, 2) for g in self.grids]}")
                    print(f"Entry Grid Level: {entry_price:.2f}")
                    print(f"Position Size: {trade_size}")
                    print(f"Exit Grid Level: {exit_price:.2f}")
                    print(f"Lower Limit: {self.lower_limit:.2f}, Upper Limit: {self.upper_limit:.2f}")
                    print(f"Profit/Loss: {trade.pl:.2f}")
                    print(f"Equity: {self.equity:.2f}")
                    print("---------------------")
                    
                    if new_buy_level and new_buy_level not in self.active_orders:
                        trade_size = self.calculate_trade_size(new_buy_level)
                        order = self.buy(size=trade_size, limit=new_buy_level)
                        self.active_orders[new_buy_level] = order
                        print(f"Sell filled and closed at {entry_price:.2f}, New Buy Order at {new_buy_level:.2f}")

        self.current_step += 1

if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)

    bt = Backtest(GOOG, GridTradingStrategy, cash=10000000000, commission=0.002, margin=0.0000000000000000000000001)
    stats = bt.run()
    bt.plot()
    print(stats)
    print(stats['_trades'])

