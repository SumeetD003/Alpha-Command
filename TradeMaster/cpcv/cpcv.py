from datetime import datetime
import time, concurrent.futures, os, sys
# Add the parent directory of TradeMaster to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
from TradeMaster.data_reader.data_reader import DataReader
from TradeMaster.backtesting import Backtest, Strategy
import pandas as pd
from itertools import combinations
import concurrent.futures
import warnings, math

class CPCV:
    def __init__(self, strategy,
                 optimization_params,
                 constraint=None,
                 maximize='Equity Final [$]', * ,
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
                 is_option: bool = False):
        self.constraint = constraint
        self.optimization_params=optimization_params
        self.strategy = strategy
        self.maximize=maximize
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
        self.reader.initialize(host='qdb.satyvm.com', port=443, https = True, username='2Cents', password='2Cents$101')
        self.num_processes = 10

    def generate_cpcv_splits(self, data, training_folds, testing_folds):
        total_folds = training_folds + testing_folds
        n_samples = len(data)
        fold_size = n_samples // total_folds
        
        # Split the data into folds
        folds = [data.iloc[i * fold_size:(i + 1) * fold_size] for i in range(total_folds)]
        
        # Generate all possible combinations of testing folds
        split_combinations = combinations(range(total_folds), testing_folds)
        
        splits = []
        
        for test_comb in split_combinations:
            train_comb = [i for i in range(total_folds) if i not in test_comb]
            train_data = pd.concat([folds[i] for i in train_comb])
            test_folds = [i for i in test_comb]
            splits.append((train_data, test_folds))
            '''
            train_data is the entire training data.
            test_folds is a list of the testing fold numbers, 0 indexed.
            '''
        
        return splits
    
    def get_paths(self, splits):
        # Get the maximum fold number
        max_fold = max(fold for _, test_folds in splits for fold in test_folds)
        available = [[] for _ in range(0,max_fold+1)]
        for i in range(0,len(splits)):
            test_folds = splits[i][1]
            for test_fold in test_folds:
                available[test_fold].append(i)
                
        paths = []
        # Constructing disjoint paths one by one now
        while True:
            if len(available[0]) == 0:
                break
            path = []
            for i in range(0,max_fold+1):
                path.append(available[i].pop())
            paths.append(path)
        return paths
    
    def split_tuples(self, data, n):
        chunk_size = math.ceil(len(data) / n)
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    
    def backtest_stockchunk(self, data_chunk):
        best_params_list = []
        for data_tuple in data_chunk:
            train_data, i = data_tuple
            bt = Backtest(train_data, self.strategy,
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
            if self.constraint is None:
                output = bt.optimize(**self.optimization_params, maximize=self.maximize)
            else:    
                output = bt.optimize(**self.optimization_params, maximize=self.maximize,constraint=self.constraint)
                
            best_params = {param: value for param, value in output._strategy._params.items() if param in self.optimization_params}
            best_params_list.append((best_params,i))
        return best_params_list
    
    def run_worker(self, data_chunk):
        test_stats_list = []
        best_params_list = data_chunk[0]
        class TestOptimizedStrategy(self.strategy):
            def init(self):
                # Initialize current_split in the constructor
                self.current_split = -1
                super().init() 
            def next(self):
                super().next() 
                if self.data.df['split_index'].iloc[-1] != self.current_split:
                    # Need to recall the init function
                    self.current_split = self.data.df['split_index'].iloc[-1]
                    for param, value in best_params_list[self.current_split].items():
                        setattr(self, param, value)
                    super().init()
                    self.indicator_attrs_np.clear()
                    
                    # Copied directly from backesting.run() to recreate the initial ds used for run function.
                    # Confirm once!
                    
                    indicator_attrs = {attr: indicator for attr, indicator in self.__dict__.items()
                           if any([indicator is item for item in self._indicators])}
                    start = max((indicator.isna().any(axis=1).argmin() if isinstance(indicator, pd.DataFrame)
                                else indicator.isna().argmin() for indicator in indicator_attrs.values()), default=0)
                    start = max(start, self._start_on_day)
                    def deframe(df): return df.iloc[:, 0] if isinstance(df, pd.DataFrame) and len(df.columns) == 1 else df
                    indicator_attrs_np = {attr: deframe(indicator).to_numpy() for attr, indicator in indicator_attrs.items()}
                    for x,y in indicator_attrs_np.items():
                        self.indicator_attrs_np[x] = y
        for data_tuple in data_chunk[1]:
            path, fold_data = data_tuple
            data_frames = []
            for i in range(0,len(path)):
                df = fold_data[i]
                df['split_index'] = path[i]
                data_frames.append(df)
            test_data = pd.concat(data_frames)

            # try:
            test_bt = Backtest(test_data, TestOptimizedStrategy,
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
            test_stats = test_bt.run()
            test_stats_list.append(test_stats)
            
        return test_stats_list
    
    def run_sequential(self, best_params_list, paths, fold_data):
        # Inherit the strategy for modified functionality   
         
        class TestOptimizedStrategy(self.strategy):
            def init(self):
                # Initialize current_split in the constructor
                self.current_split = -1
                super().init() 
            def next(self):
                super().next() 
                if self.data.df['split_index'].iloc[-1] != self.current_split:
                    # Need to recall the init function
                    self.current_split = self.data.df['split_index'].iloc[-1]
                    for param, value in best_params_list[self.current_split].items():
                        setattr(self, param, value)
                    super().init()
                    self.indicator_attrs_np.clear()
                    
                    # Copied directly from backesting.run() to recreate the initial ds used for run function.
                    # Confirm once!
                    
                    indicator_attrs = {attr: indicator for attr, indicator in self.__dict__.items()
                           if any([indicator is item for item in self._indicators])}
                    start = max((indicator.isna().any(axis=1).argmin() if isinstance(indicator, pd.DataFrame)
                                else indicator.isna().argmin() for indicator in indicator_attrs.values()), default=0)
                    start = max(start, self._start_on_day)
                    def deframe(df): return df.iloc[:, 0] if isinstance(df, pd.DataFrame) and len(df.columns) == 1 else df
                    indicator_attrs_np = {attr: deframe(indicator).to_numpy() for attr, indicator in indicator_attrs.items()}
                    for x,y in indicator_attrs_np.items():
                        self.indicator_attrs_np[x] = y
                        
        for path in paths:
            # First construct the testing data for the path.
            data_frames = []
            for i in range(0,len(path)):
                df = fold_data[i]
                df['split_index'] = path[i]
                data_frames.append(df)
            test_data = pd.concat(data_frames)

            test_bt = Backtest(test_data, TestOptimizedStrategy,
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
            test_stats = test_bt.run()
            self.test_stats_list.append(test_stats)
            
    def run_parallel(self, best_params_list, paths, fold_data):
        # Parallelizing the path executions
        data_tuples = [(path, fold_data) for path in paths]
        data_chunks = list(self.split_tuples(data_tuples, self.num_processes))

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_processes) as executor:
            futures = [executor.submit(self.run_worker, (best_params_list, data_chunk)) for data_chunk in data_chunks]
            
            for future in concurrent.futures.as_completed(futures):
                t = future.result() 
                for result in t:
                    self.test_stats_list.append(result)
        

    def run(self, stock, timeframe, market, exchange = None, training_folds = 4, testing_folds = 1):
        stock = stock.upper()
        # First get data for the stock
        try:
            data = self.reader.fetch_stock(stock, timeframe, market, exchange)
            print("Data fetched for", stock)
        except Exception as e:
            print(f"Error fetching data for {stock}: {e}")
            raise
        splits = self.generate_cpcv_splits(data, training_folds, testing_folds)
        paths = self.get_paths(splits)
        
        total_folds = training_folds + testing_folds
        n_samples = len(data)
        fold_size = n_samples // total_folds
        
        # Store the data corresponding to each fold
        fold_data = []
        for i in range(total_folds):
            fold_data.append(data.iloc[i * fold_size:(i + 1) * fold_size])        
        
        num_splits = len(splits)
        best_params_list = [0 for i in range(0,num_splits)]

        # Find best parameter setting for all the splits in parallel.
        
        data_tuples = []
        for i in range(0, num_splits):
            data_tuples.append((splits[i][0], i))
            
        data_chunks = self.split_tuples(data_tuples, self.num_processes)
            
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            # Map the tasks to the stock name for later on
            futures = [executor.submit(self.backtest_stockchunk, data_chunk) for data_chunk in data_chunks]
            
            for future in concurrent.futures.as_completed(futures):
                t = future.result() 
                for best_param, i in t:
                    best_params_list[i] = best_param
            
        self.test_stats_list = []          
        
        self.run_sequential(best_params_list, paths, fold_data)
        # self.run_parallel(best_params_list, paths, fold_data)
        
        stats_df = pd.DataFrame(self.test_stats_list)
        stats_df = stats_df.drop(columns=["_equity_curve", "_trades", "_orders"], errors="ignore")
        # Compute statistical metrics for numerical columns
        metrics = {}
        for column in stats_df.select_dtypes(include="number").columns:
            column_data = stats_df[column].dropna()  # Exclude NaN values
            metrics[column] = {
                "Mean": column_data.mean(),
                "Median": column_data.median(),
                "Max": column_data.max(),
                "Min": column_data.min(),
                "Standard Deviation": column_data.std()
            }
        
        summary = pd.DataFrame(metrics).T  
        summary.index.name = "Metric"
        # print(summary)
        
        # Create an Excel file with two sheets: 'results' and 'summary'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_directory = os.getcwd()
        output_directory = os.path.join(output_directory, f'cpcv_output_{timestamp}')
        os.makedirs(output_directory)
        print("Output saved to",output_directory)
        file_path = os.path.join(output_directory, 'output.xlsx')
        with pd.ExcelWriter(file_path) as writer:
            stats_df.to_excel(writer, sheet_name='results', index=False)
            summary.to_excel(writer, sheet_name='summary')
        
        

if __name__ == '__main__':
    print("Here in main")