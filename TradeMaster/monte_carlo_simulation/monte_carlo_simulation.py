import numpy as np
import pandas as pd
from TradeMaster.backtesting import Backtest
import matplotlib.pyplot as plt
from TradeMaster.data_reader.data_reader import DataReader
import os, random
from datetime import datetime
import concurrent.futures

class MonteCarloSimulation:
    def __init__(self, strategy, * ,
                 cash: float = 10_000,
                 holding: dict = {},
                 commission: float = .0,
                 margin: float = 1.,
                 trade_on_close=False,
                 hedging=False,
                 exclusive_orders=False,
                 trade_start_date=None,
                 lot_size=1,
                 fail_fast=True,
                 storage: dict | None = None,
                 is_option: bool = False
                 ):
        self.strategy = strategy
        self.cash = cash
        self.commission = commission
        self.holding = holding
        self.margin = margin
        self.trade_on_close = trade_on_close
        self.hedging = hedging
        self.exclusive_orders = exclusive_orders
        self.trade_start_date = trade_start_date
        self.lot_size= lot_size
        self.fail_fast = fail_fast
        self.storage = storage
        self.is_option = is_option 
        self.reader = DataReader()
        self.reader.initialize(host='qdb.satyvm.com', https = True, port=443, username='2Cents', password='2Cents$101')
        self.num_processes = 10
        
    def simulate_stock_worker(self, data_tuple):
        original_data, num_simulations = data_tuple
        simulation_results = []
        equity_curves = []
        all_stats = []
        for i in range(0, num_simulations):
            if self.shuffle_by == 'per':
                shuffled_data = self._shuffle_returns_per(original_data.copy())
            else:
                shuffled_data = self._shuffle_returns_price(original_data.copy())

            # Run the backtest with the shuffled data
            bt = Backtest(shuffled_data, self.strategy, cash = self.cash,
                            commission = self.commission,
                            holding = self.holding,
                            margin = self.margin,
                            trade_on_close = self.trade_on_close,
                            hedging = self.hedging,
                            exclusive_orders = self.exclusive_orders,
                            trade_start_date = self.trade_start_date,
                            lot_size= self.lot_size,
                            fail_fast = self.fail_fast,
                            storage = self.storage,
                            is_option = self.is_option
                            )
            stats = bt.run()
            simulation_results.append(stats['Equity Final [$]'])
            equity_curves.append(stats['_equity_curve']['Equity'].values)
            all_stats.append(stats)
        return (simulation_results, equity_curves, all_stats)
    
    def simulate_stock(self, stock, timeframe, market, exchange = None, num_simulations = 100, shuffle_by = 'per'):
        """
        Will support shuffling by two methods: by percentage(per) and by price(price).
        Prints the stats. Stores summary in output directory.
        """    
        self.stock = stock
        self.shuffle_by = shuffle_by
        data = self.reader.fetch_stock(stock, timeframe, market, exchange)
        print("Data fetched for",stock)
        self.num_simulations = num_simulations
        self.simulation_results = []
        self.equity_curves = []
        self.all_stats = []  # Store stats for each simulation
        
        original_data = data.copy()
        l = num_simulations // self.num_processes
        h = l + 1
        h_num = num_simulations % self.num_processes
        l_num = self.num_processes - h_num
        
        data_tuples = []
        for i in range(0,l_num):
            data_tuples.append((original_data.copy(), l))
        for i in range(0,h_num):
            data_tuples.append((original_data.copy(), h))
        
        with concurrent.futures.ProcessPoolExecutor(max_workers = self.num_processes) as executor:
            futures = [executor.submit(self.simulate_stock_worker, data) for data in data_tuples]
            
            for future in concurrent.futures.as_completed(futures):
                t = future.result() 
                sz = len(t)
                for i in range(0,sz):
                    self.simulation_results.append(t[0][i])
                    self.equity_curves.append(t[1][i])
                    self.all_stats.append(t[2][i])

        self.analyze_results()
        self.create_stats_sheet()

    def _store_price_percentages(self, data):
        """
        Store Open-to-Close, High-to-Close, and Low-to-Close percentages in a dictionary for each candle.
        """
        price_perc_dict = {}
        for index, row in data.iterrows():
            open_close_pct = (row['Open'] - row['Close']) / row['Close'] * 100
            high_close_pct = (row['High'] - row['Close']) / row['Close'] * 100
            low_close_pct = (row['Close'] - row['Low']) / row['Close'] * 100
            price_perc_dict[index] = {
                'open_close_pct': open_close_pct,
                'high_close_pct': high_close_pct,
                'low_close_pct': low_close_pct
            }
        return price_perc_dict
    
    def _shuffle_returns_per(self, data):
        """
        Shuffle the open-to-close return percentages and calculate new prices based on shuffled returns.
        """
        price_perc_dict = self._store_price_percentages(data)
        
        # Shuffle the Open-to-Close percentages
        shuffled_open_close_pct = np.random.permutation([v['open_close_pct'] for v in price_perc_dict.values()])

        # Initialize new Close prices (skip first index as we don't shuffle the first value)
        new_close_prices = [data['Close'].iloc[0]]  # Start from the first known Close price

        # Calculate new Close prices based on the shuffled open-close percentages
        for pct in shuffled_open_close_pct:
            new_close_prices.append(new_close_prices[-1] / (1 + pct / 100))

        # Make sure to drop the last value to match the length of data.index
        new_close_prices = new_close_prices[:len(data)]  # Ensure the length matches exactly

        # Now convert the list to a pandas Series with the correct index
        new_close_prices = pd.Series(new_close_prices, index=data.index)

        data['Close'] = new_close_prices

        # Rebuild Open, High, and Low prices using the original percentages
        for i, index in enumerate(data.index[1:]):  # Skip the first row (no return for the first)
            data.at[index, 'Open'] = data.at[index, 'Close'] * (1 + price_perc_dict[index]['open_close_pct'] / 100)
            data.at[index, 'High'] = data.at[index, 'Close'] * (1 + price_perc_dict[index]['high_close_pct'] / 100)
            data.at[index, 'Low'] = data.at[index, 'Close'] * (1 - price_perc_dict[index]['low_close_pct'] / 100)

        return data
    
    def _shuffle_returns_price(self, data):
        # price_perc_dict = self._store_price_percentages(data)
        n = len(data)
        new_close_prices = [data['Close'].iloc[0]] # Starting with the original price
        # Now finding the price changes over time
        price_changes = []
        new_open_prices = [data['Open'].iloc[0]]
        new_low_prices = [data['Low'].iloc[0]]
        new_high_prices = [data['High'].iloc[0]]
        for i in range(1,n):
            price_changes.append((data['Close'].iloc[i] - data['Close'].iloc[i-1], data['Close'].iloc[i]-data['Open'].iloc[i],
                                  data['Close'].iloc[i]-data['Low'].iloc[i], data['Close'].iloc[i]-data['High'].iloc[i]))
            
        random.shuffle(price_changes)
        
        for delta_tuple in price_changes:
            new_close_prices.append(new_close_prices[-1] + delta_tuple[0])
            new_open_prices.append(new_close_prices[-1] - delta_tuple[1])
            new_low_prices.append(new_close_prices[-1] - delta_tuple[2])
            new_high_prices.append(new_close_prices[-1] - delta_tuple[3])
            
        new_close_prices = pd.Series(new_close_prices, index=data.index)
        new_open_prices = pd.Series(new_open_prices, index=data.index)
        new_low_prices = pd.Series(new_low_prices, index=data.index)
        new_high_prices = pd.Series(new_high_prices, index=data.index)
        # print(data)
        data['Close'] = new_close_prices
        data['Open'] = new_open_prices
        data['Low'] = new_low_prices
        data['High'] = new_high_prices
        # print(data)
        
        return data

    def analyze_results(self):
        """
        Analyze the Monte Carlo results (mean, standard deviation, etc.).
        Print the analytics.
        """
        results = np.array(self.simulation_results)
        mean = np.mean(results)
        stddev = np.std(results)
        min_value = np.min(results)
        max_value = np.max(results)
        median_value = np.median(results)

        print(f"Monte Carlo Simulation Results over {self.num_simulations} runs:")
        print(f"Mean Final Equity: {mean:.2f}")
        print(f"Median Final Equity: {median_value:.2f}")
        print(f"Standard Deviation: {stddev:.2f}")
        print(f"Min Final Equity: {min_value:.2f}")
        print(f"Max Final Equity: {max_value:.2f}")

    def create_stats_sheet(self):
        """
        Create a stats summary sheet with min, max, median, average of all numerical parameters.
        Stores them in a csv file. Print its path as well.
        """
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_directory = os.path.join(os.getcwd(),f'monte_carlo_simulation_output_{timestamp}')
        os.makedirs(output_directory)
        print("Output saved to",output_directory)
        self.output_directory = output_directory
        filename = os.path.join(output_directory,'summary.xlsx')
        
        df_results = pd.DataFrame(self.all_stats)
        numerical_df = df_results.select_dtypes(include=['number'])
        summary_stats = {
            'mean': numerical_df.mean(),
            'median': numerical_df.median(),
            "Standard Deviation": numerical_df.std(),
            'min': numerical_df.min(),
            'max': numerical_df.max()
        }

        summary_df = pd.DataFrame(summary_stats)
        summary_df.to_excel(filename, index=True)

        print(f"Summary statistics for the simulation have been saved to {filename}")
        self.plot()

    def plot(self, default_curve=None, opimised_curve=None):
        """
        Plots a histogram of the final equity values from the Monte Carlo simulation.
        """
        plt.figure(figsize=(10, 6))
        plt.hist(self.simulation_results, bins=20, alpha=0.75, color='blue', edgecolor='black')
        plt.title('Monte Carlo Simulation: Distribution of Final Equity')
        plt.xlabel('Final Equity ($)')
        plt.ylabel('Frequency')
        plt.grid(True)
        save_path = os.path.join(self.output_directory, f"{self.stock}_histogram.png")
        plt.savefig(save_path)
        # plt.show()
        self.plot_equity_curves(default_curve,opimised_curve)
        
    def plot_equity_curves(self,default_equity_curve=None, optimized_equity_curve=None):
        """
        Plot all equity curves from the Monte Carlo simulations on a single graph.
        """
        plt.figure(figsize=(10, 6))
        for equity_curve in self.equity_curves:
            plt.plot(equity_curve, alpha=0.3)  # Plot each equity curve with some transparency
        if default_equity_curve is not None:
            plt.plot(default_equity_curve, color='black', label='Default Equity', linewidth=2)

        # Plot optimized equity curve in green
        if optimized_equity_curve is not None:
            plt.plot(optimized_equity_curve, color='green', label='Optimized Equity', linewidth=2)

        plt.title('Monte Carlo Simulation: All Equity Curves')
        plt.xlabel('Time (Bars)')
        plt.ylabel('Equity ($)')
        plt.grid(True)
        save_path = os.path.join(self.output_directory, f"{self.stock}_equity_curve.png")
        plt.savefig(save_path)
        # plt.show()