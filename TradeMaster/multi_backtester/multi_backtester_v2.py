import shutil, time, concurrent.futures, os, sys, traceback
# Add the parent directory of TradeMaster to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pandas as pd
from TradeMaster.data_reader.data_reader import DataReader
from TradeMaster.backtesting import Backtest
from queue import Queue
from multiprocessing import Pool, cpu_count
from datetime import datetime
import time, sys, asyncio, nest_asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
nest_asyncio.apply()


'''
Uses async. Data fetched and backtesting is done together.
'''

class MultiBacktest:
    def __init__(self, strategy, universe_name, timeframe, exchange_name = None, * ,
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
        self.universe = universe_name
        self.timeframe = timeframe
        self.strategy = strategy
        self.exchange = exchange_name
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
        self.results = []


    async def backtest_single_stock(self, data_tuple):
        stock, timeframe, market, exchange, keyword_args = data_tuple
        print("Backtest started",stock)
        try:
            data = self.reader.fetch_stock(stock, timeframe, market, exchange)
        except Exception as e:
            print(f"Error while fetching data for {stock}",e)
            return None
        print("Data fetched for",stock)
        if len(data) == 0:
            return None # If no data returned, do not backtest as Backtest expects a non empty dataset 
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
        except Exception as e:
            print("Error while backtesting",stock,e)
            return None
        print("Backtest finishes for",stock)
        result = bt.run(**keyword_args) # Pass the keyword arguments additionally passed
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{stock}_{timestamp}.html'
        output_tearsheet_filepath = os.path.join(self.output_tearsheet_directory, filename)
        # bt.tear_sheet(results= result, webbrowser_open = False, output_path = output_tearsheet_filepath)
        return (stock, bt, result, output_tearsheet_filepath)
    
    def backtest_single_stock_helper(self, data_tuple):
        result = asyncio.run(self.backtest_single_stock(data_tuple))
        return result

    def create_tearsheets(self):
         for data in self.results:
            stock, bt, result, output_tearsheet_filepath = data
            try:
                bt.tear_sheet(results=result, webbrowser_open=False, output_path=output_tearsheet_filepath)
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
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_directory, f"summary_{timestamp}.xlsx")
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Stock Results")
            metrics_df.to_excel(writer, sheet_name="Metrics")
        
        print(f"Summary sheet saved to {output_path}")


    def run(self, **kwargs):
        """
        Runs the strategy on all the stocks under the universe. 
        Returns a dictionary containing a pandas series for each stock containing strategy performance parameters
        """
        stock_list, market = self.reader.fetch_stocks(self.universe)
        
        print(len(stock_list))

        # Determine the directory of the strategy.py file
        caller_frame = traceback.extract_stack()[-2]  # Get the second-last frame in the call stack
        strategy_file_path = caller_frame.filename  # Path of the script calling the current code (strategy.py)
        strategy_directory = os.path.dirname(os.path.realpath(strategy_file_path))  # Directory of strategy.py
        
        output_directory_path = os.path.join(strategy_directory, 'multibacktester_output')
        if os.path.exists(output_directory_path):
            shutil.rmtree(output_directory_path)
        os.makedirs(output_directory_path)

        # Set the output directory to 'output_tearsheets' under strategy.py's directory
        output_tearsheet_directory = os.path.join(output_directory_path, 'output_tearsheets')
        self.output_tearsheet_directory = output_tearsheet_directory
        os.makedirs(output_tearsheet_directory)

        data_tuples = []
        for stock in stock_list:
            keyword_args = kwargs
            data_tuples.append((stock, self.timeframe, market, self.exchange, keyword_args))

        # self.process_sequential(data_tuples)

        # Execute the backtest function in parallel using ThreadPoolExecutor
        start_time = time.time()
        self.results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            # Map the tasks to the stock name for later on
            futures = {executor.submit(self.backtest_single_stock_helper, data_tuple): data_tuple[0] for data_tuple in data_tuples}
            
            for future in concurrent.futures.as_completed(futures):
                stock = futures[future]
                try:
                    t = future.result() 
                    if t is not None:
                        self.results.append(t)
                except Exception as e:
                    print(f"Error occurred while backtesting {stock}: {e}")


        end_time = time.time()
        print(f'Elapsed: {end_time - start_time}')

        self.generate_summary(output_directory_path)

        # Create tearsheets in main thread because of Tkinter in python.
        self.create_tearsheets()

        


# testing
if __name__ == "__main__":
    print("Here in main")
    start_time = time.time()
    
    end_time = time.time()
    print(f"Elapsed time: {end_time - start_time}")