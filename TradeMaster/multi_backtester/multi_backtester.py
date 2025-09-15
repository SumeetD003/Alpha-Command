import time, concurrent.futures, os, sys
# Add the parent directory of TradeMaster to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
from TradeMaster.data_reader.data_reader import DataReader
from TradeMaster.backtesting import Backtest
from datetime import datetime
import math, json
import warnings
'''
Data is fetched at once and then passed during multiprocessing for backtesting.
'''

class MultiBacktest:
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
                 is_option: bool = False ):
        """
        Takes as input the universe, timeframe and optional exchange name. 
        Fetches all datasets correspondingly, and thereafter runs the strategy on all 
        of them. Finally generates all tearsheets in the same directory of run.

        strategy, cash, commission forced as keyword arguments. 
        This allows exchange to be an optional parameter in the middle of the parameter list
        """

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
        self.reader.initialize(host='qdb.satyvm.com', https = True, port=443, username='2Cents', password='2Cents$1012cc')
        self.results = []
        self.num_processes = 4

    def get_root_dir(self):
        return os.getcwd()

    def backtest_stock(self, stock, timeframe, market, exchange = None, **kwargs):
        if timeframe.lower() == 'all':
            return self.backtest_stock_mtf(stock, market, exchange, **kwargs)
        data = self.reader.fetch_stock(stock, timeframe, market, exchange)
        if len(data) == 0:
            print("No data available for the given specifications")
            return
        print("Data fetched")
        bt = Backtest(data, self.strategy,
                    cash = self.cash,
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
        result = bt.run(**kwargs) # Pass the keyword arguments additionally passed
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{stock}_tearsheet.html'
        output_directory_path = self.get_root_dir()
        output_directory_path = os.path.join(output_directory_path, f'multibacktester_output_{timestamp}')
        os.makedirs(output_directory_path)
        output_tearsheet_filepath = os.path.join(output_directory_path, filename)
        warnings.filterwarnings("ignore", category=FutureWarning)
        try:
            bt.tear_sheet(results= result, open_browser = False, output_path = output_tearsheet_filepath)
            print("Tearsheet generated and saved to",output_tearsheet_filepath)
        except Exception as e:
            print("Error while generating tearsheet for",stock,e)
        try:
            output_plot_filepath = os.path.join(output_directory_path, f'{stock}_plot.html')
            bt.plot(filename=output_plot_filepath, open_browser=False)
        except Exception as e:
            print("Error while generating plot",e)
        return result
    
    def split_list(self, data, n):
        chunk_size = math.ceil(len(data) / n)
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

    def backtest_stockchunk(self, data_chunk):
        results = []
        for data_tuple in data_chunk:
            stock, data, keyword_args = data_tuple
            if len(data) == 0:
                print("No data for",stock)
                continue
            print("Backtesting started for",stock)
            try:
                bt = Backtest(data, self.strategy,
                                cash = self.cash,
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
                result = bt.run(**keyword_args) # Pass the keyword arguments additionally passed
            except Exception as e:
                print("Error while backtesting",stock,e)
                continue
            print("Backtest finishes for",stock)

            filename = f'{stock}_tearsheet.html'
            output_tearsheet_filepath = os.path.join(self.output_tearsheet_directory, filename)
            results.append((stock, bt, result, output_tearsheet_filepath))
            try:
                bt.tear_sheet(results= result, open_browser = False, output_path = output_tearsheet_filepath)
                print("Tearsheet generated for",stock)
            except Exception as e:
                print("Error while generating tearsheet for",stock,e)
            try:
                bt.plot(filename = os.path.join(self.output_plot_directory, f'{stock}_plot.html'), open_browser=False)
            except Exception as e:
                print("Error while generating plot",stock,e)
        return results

    def create_tearsheets(self):
         for data in self.results:
            stock, bt, result, output_tearsheet_filepath = data
            try:
                bt.tear_sheet(results=result, open_browser = False, output_path=output_tearsheet_filepath)
                print(f"Tearsheet generated for {stock}")
            except Exception as e:
                print(f"Error occurred while generating tearsheet for {stock}: {e}")

    def create_single_tearsheet(self, data_tuple):
        stock, bt, result, output_tearsheet_filepath = data_tuple
        try:
            bt.tear_sheet(results=result, webbrowser_open=False, output_path=output_tearsheet_filepath)
            print(f"Tearsheet generated for {stock}")
        except Exception as e:
            print(f"Error occurred while generating tearsheet for {stock}: {e}")

    def process_sequential(self, data_tuples):
        for data in data_tuples:
            try:
                self.backtest_single_stock(data)
                print(f"Backtest completed for {data[0]}")
            except Exception as e:
                print(f"Error occurred while backtesting {data[0]}: {e}")

    def generate_summary(self, output_directory):
        # Create a DataFrame from results
        stock_data = []
        stock_names = []
        for _ in self.results:
            result_series =  _[2]
            stock_name = _[0]
            stock_data.append(result_series)
            stock_names.append(stock_name)
        df = pd.DataFrame(stock_data, index=stock_names)
        df.index.name = "Stock"
        
        # Drop unwanted columns
        df = df.drop(columns=["_equity_curve", "_trades", "_orders"], errors="ignore")
        
        # Compute statistical metrics for numerical columns
        metrics = {}
        for column in df.select_dtypes(include="number").columns:
            column_data = df[column].dropna()  # Exclude NaN values
            metrics[column] = {
                "Mean": column_data.mean(),
                "Median": column_data.median(),
                "Max": column_data.max(),
                "Min": column_data.min(),
                "Standard Deviation": column_data.std(),
                "Top 10 Percentile Average": column_data[column_data >= column_data.quantile(0.9)].mean(),
                "Top 25 Percentile Average": column_data[column_data >= column_data.quantile(0.75)].mean(),
                "Top 50 Percentile Average": column_data[column_data >= column_data.quantile(0.5)].mean(),
                "Top 75 Percentile Average": column_data[column_data >= column_data.quantile(0.25)].mean(),
            }
        
        metrics_df = pd.DataFrame(metrics).T  
        metrics_df.index.name = "Metric"
        
        # Save to CSV with two sheets
        output_path = os.path.join(output_directory, f"summary.xlsx")
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Stock Results")
            metrics_df.to_excel(writer, sheet_name="Metrics")
        
        print(f"Summary sheet saved to {output_path}")

    def backtest_universe(self, universe, timeframe, exchange = None, **kwargs):
        """
        Runs the strategy on all the stocks under the universe. 
        Returns a dictionary containing a pandas series for each stock containing strategy performance parameters
        """
        if timeframe.lower() == 'all':
            return self.backtest_universe_mtf(universe, exchange, **kwargs)
        data = self.reader.fetch_universe(universe, timeframe, exchange)
        print("Data fetched for universe",universe)
        warnings.filterwarnings("ignore", category=FutureWarning)
        output_root_directory = self.get_root_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_directory_path = os.path.join(output_root_directory, f'multibacktester_output_{timestamp}')
        output_tearsheet_directory = os.path.join(output_directory_path, f'output_tearsheets')
        self.output_tearsheet_directory = output_tearsheet_directory
        os.makedirs(output_tearsheet_directory)
        
        output_plot_directory = os.path.join(output_directory_path, f'output_plots')
        self.output_plot_directory = output_plot_directory
        os.makedirs(output_plot_directory)
        

        num_processes = self.num_processes

        data_tuples = [(stock, stock_data, kwargs) for (stock,stock_data) in data.items()]
        data_chunks = list(self.split_list(data_tuples, num_processes))
        # Execute the backtest function in parallel using ProcessPoolExecutor
        start_time = time.time()
        self.results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
            # Map the tasks to the stock name for later on
            futures = [executor.submit(self.backtest_stockchunk, data_chunk) for data_chunk in data_chunks]
            
            for future in concurrent.futures.as_completed(futures):
                t = future.result() 
                for result in t:
                    self.results.append(result)
                    
        end_time = time.time()
        
        print('Output saved to',output_directory_path)
        self.generate_summary(output_directory_path)
        
    def backtest_universe_mtf_worker(self, data_tuple):
        stock, market, exchange, kwargs = data_tuple
        # Backtest for all timeframes sequentially
        data_all = self.reader.fetch_stock_alltfs(stock, market, exchange)
        results = []
        for timeframe, data in data_all.items():
            print("Started",stock,timeframe)
            bt = Backtest(data, self.strategy,
                    cash = self.cash,
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
            result = bt.run(**kwargs) # Pass the keyword arguments additionally passed
            try:
                bt.plot(filename = os.path.join(self.output_plot_directory, f'{stock}_{timeframe}_plot.html'), open_browser=False)
            except Exception as e:
                print(f"Error while plotting {stock} {timeframe}",e)
            filename = f'{stock}_{timeframe}_tearsheet.html'
            output_tearsheet_filepath = os.path.join(self.output_tearsheet_directory, filename)
            try:
                bt.tear_sheet(results= result, open_browser = False, output_path = output_tearsheet_filepath)
                print(f"Tearsheet generated for {stock} {timeframe} and saved to {output_tearsheet_filepath}")
            except Exception as e:
                print("Error while generating tearsheet for",stock,timeframe,e)
            results.append((stock, timeframe, result))
            print("Done",stock,timeframe)
        return results
        
        
    def backtest_universe_mtf(self, universe, exchange = None, **kwargs):
        stock_list, market = self.reader.fetch_stocks(universe)
        output_root_directory = self.get_root_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_directory_path = os.path.join(output_root_directory, f'multibacktester_output_{timestamp}')
        output_tearsheet_directory = os.path.join(output_directory_path, f'output_tearsheets')
        self.output_tearsheet_directory = output_tearsheet_directory
        os.makedirs(output_tearsheet_directory)
        
        output_plot_directory = os.path.join(output_directory_path, f'output_plots')
        self.output_plot_directory = output_plot_directory
        os.makedirs(output_plot_directory)
        
        print('Output saved to',output_directory_path)
        
        data_tuples = [(stock, market, exchange, kwargs) for stock in stock_list]
        num_processes = self.num_processes

        start_time = time.time()
        self.results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
            # Map the tasks to the stock name for later on
            futures = [executor.submit(self.backtest_universe_mtf_worker, data_tuple) for data_tuple in data_tuples]
            for future in concurrent.futures.as_completed(futures):
                t = future.result() 
                self.results.append(t)
                    
        end_time = time.time()
        print("Elapsed:",end_time-start_time)
        
        summary_path = os.path.join(output_directory_path, "summary.xlsx")
        with pd.ExcelWriter(summary_path, engine="openpyxl") as writer:
            data_by_timeframe = {}
            for sublist in self.results:
                for stock, timeframe, result in sublist:
                    if timeframe not in data_by_timeframe:
                        data_by_timeframe[timeframe] = {}
                    data_by_timeframe[timeframe][stock] = result

            # Create a subsheet for each timeframe
            for timeframe, stock_data in data_by_timeframe.items():
                timeframe_df = pd.DataFrame(stock_data)
                timeframe_df = timeframe_df.T
                timeframe_df.to_excel(writer, sheet_name=timeframe)

        print(f"Summary Excel file saved to {output_directory_path}")

    def generate_summary_mtf(self, output_directory):
        summary_data = []
        for _ in self.results:
            row = {"Stock": _[0], "Timeframe": _[1]}
            row.update(_[2].to_dict())  # Add all metrics as columns
            summary_data.append(row)
            
        # Create a DataFrame
        df = pd.DataFrame(summary_data)
        # Save to Excel
        output_file = os.path.join(output_directory,"summary.xlsx")
        df.to_excel(output_file, index=False)

        print(f"Summary saved to {output_file}")      
        
    def backtest_stock_mtf_worker(self, data_tuple):
        stock, timeframe, data, kwargs = data_tuple
        bt = Backtest(data, self.strategy,
                    cash = self.cash,
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
        result = bt.run(**kwargs) # Pass the keyword arguments additionally passed
        filename = f'{stock}_{timeframe}_tearsheet.html'
        output_tearsheet_filepath = os.path.join(self.output_tearsheet_directory, filename)
        try:
            bt.plot(filename = os.path.join(self.output_plot_directory, f'{stock}_{timeframe}_plot.html'), open_browser=False)
        except Exception as e:
            print(f"Error while plotting {stock} {timeframe}",e)
            raise
        try:
            bt.tear_sheet(results= result, open_browser = False, output_path = output_tearsheet_filepath)
            print(f"Tearsheet generated for timeframe {timeframe} and saved to {output_tearsheet_filepath}")
        except Exception as e:
            print("Error while generating tearsheet for",stock,timeframe,e)
        return (stock, timeframe, result)
        
    def backtest_stock_mtf(self, stock, market, exchange = None, **kwargs):
        market = market.lower()
        try:
            data = self.reader.fetch_stock_alltfs(stock, market, exchange)
        except Exception as e:
            print(f"Error while fetching data for {stock} {e}")
            raise
        print("Data fetched for",stock)
        # Create output directory
        output_root_directory = self.get_root_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_directory_path = os.path.join(output_root_directory, f'multibacktester_output_{timestamp}')
        output_tearsheet_directory = os.path.join(output_directory_path, f'output_tearsheets')
        self.output_tearsheet_directory = output_tearsheet_directory
        os.makedirs(output_tearsheet_directory)
        
        output_plot_directory = os.path.join(output_directory_path, f'output_plots')
        self.output_plot_directory = output_plot_directory
        os.makedirs(output_plot_directory)
        
        print('Output saved to',output_directory_path)
        
        num_processes = self.num_processes
        
        data_tuples = [(stock, timeframe, stock_data, kwargs) for (timeframe, stock_data) in data.items()]
        start_time = time.time()
        self.results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
            # Map the tasks to the stock name for later on
            futures = [executor.submit(self.backtest_stock_mtf_worker, data_tuple) for data_tuple in data_tuples]
            
            for future in concurrent.futures.as_completed(futures):
                t = future.result() 
                self.results.append(t)
                    
        end_time = time.time()
        print("Elapsed:",end_time-start_time)
        # print(self.results)
        
        # Generate summary sheet
        self.generate_summary_mtf(output_directory_path)
        
        
        


# testing
if __name__ == "__main__":
    print("Here in main")
    start_time = time.time()
    # bt = MultiBacktest("AdxTrendStrategy", cash = 100000, commission = 0.002, margin = 1/100)
    # bt.backtest_stock_mtf('AAPL', 'us', 'firstratedata')
    end_time = time.time()
    print(f"Elapsed time: {end_time - start_time}")