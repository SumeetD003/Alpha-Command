import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import os, sys, pandas as pd, traceback, shutil, concurrent.futures
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from TradeMaster import quantstats
from TradeMaster._plotting import plot
from TradeMaster._stats import compute_stats
from TradeMaster.backtesting import Backtest
from TradeMaster.data_reader.data_reader import DataReader
from threading import Lock
import time, math
from datetime import datetime


class WalkForwardOptimizer:
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

    def get_period_dates(self, start_date, period):
        if period[-1] == 'M':
            months = int(period[:-1])
            end_date = start_date + pd.DateOffset(months=months)
        elif period[-1] == 'D':
            days = int(period[:-1])
            end_date = start_date + pd.DateOffset(days=days)
        elif period[-1] == 'H':
            hours = int(period[:-1])
            end_date = start_date + pd.DateOffset(hours=hours)
        else:
            raise ValueError("Unsupported period format, use 'M' for months, 'D' for days, or 'H' for hours")
        return end_date

    def optimize(self, strategy_class, optimization_params, data, training_candles, testing_candles):
        total_candles = len(data)
        current_candle_index = 0
        start_date = data.index[current_candle_index]
        if current_candle_index + training_candles - 1 < total_candles:
            end_date = data.index[current_candle_index + training_candles - 1]
        else:
            end_date = datetime.max
        if current_candle_index + training_candles + testing_candles - 1 < total_candles:
            test_end_date = data.index[current_candle_index + training_candles + testing_candles - 1]
        else:
            test_end_date = datetime.max

        results_list = []
        trades_list = []
        equity_curves=[]
        orders_list=[]
        stats=[]
        
        while test_end_date <= data.index[-1]:
            
            train_data = data[start_date:end_date]
            test_data = data[start_date:test_end_date] # Date adjusted for complete computation of indicators
            # try:
            bt = Backtest(train_data, strategy_class,
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
                output = bt.optimize(**optimization_params, maximize=self.maximize)
            else:    
                output = bt.optimize(**optimization_params, maximize=self.maximize,constraint=self.constraint)
            # except Exception as e:
                # print(f"Error during optimisation {e}")
                # return
                
            best_params = {param: value for param, value in output._strategy._params.items() if param in optimization_params}

            class TrainOptimizedStrategy(strategy_class):
                def init(self):
                    for param, value in best_params.items():
                        setattr(self, param, value)
                    super().init()
                   
            class TestOptimizedStrategy(strategy_class):
                def init(self):
                    for param, value in best_params.items():
                        setattr(self, param, value)
                    super().init()
                def next(self):
                    if self.data.index[-1] < end_date:
                        pass
                    super().next()
            
            train_bt = Backtest(train_data, TrainOptimizedStrategy,
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
            train_stats = train_bt.run()

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

            trades = test_stats['_trades']
            trades['Period'] = f"{start_date} to {test_end_date}"
            trades_list.append(trades)
            
            orders_list.append(test_stats['_orders'])
            
            equity_curve = test_stats['_equity_curve']['Equity']
            equity_curve = equity_curve[equity_curve.index >= end_date]
            
            equity_pct_change = equity_curve.pct_change().dropna()
            equity_curves.append(equity_pct_change) 

            train_summary_stats = train_stats.to_dict()
            train_summary_stats.update({
                "Start Date": train_data.index[0],
                "End Date": train_data.index[-1],
                "Type": "Training",
            })
            train_summary_stats.update(best_params)

            test_summary_stats = test_stats.to_dict()
            test_summary_stats.update({
                "Start Date": train_data.index[-1],
                "End Date": test_data.index[-1],
                "Type": "Testing",
            })
            test_summary_stats.update(best_params)

            results_list.append(train_summary_stats)
            results_list.append(test_summary_stats)

            current_candle_index += testing_candles # Dummy comment added
            if current_candle_index < total_candles:
                start_date = data.index[current_candle_index]
            else:
                start_date = datetime.max
            if current_candle_index + training_candles - 1 < total_candles:
                end_date = data.index[current_candle_index + training_candles - 1]
            else:
                end_date = datetime.max
            if current_candle_index + training_candles + testing_candles - 1 < total_candles:
                test_end_date = data.index[current_candle_index + training_candles + testing_candles - 1]
            else:
                test_end_date = datetime.max
            # start_date = test_end_date
            # end_date = self.get_period_dates(start_date, training_period)
            # test_end_date = self.get_period_dates(end_date, testing_period)
            
        if (len(orders_list)):    
            df_orders = pd.concat(orders_list, ignore_index = True)

        df_results = pd.DataFrame(results_list)
        df_results = df_results[['Start Date', 'End Date', 'Type'] + [col for col in df_results.columns if col not in ['Start Date', 'End Date', 'Type']]]

        df_results.loc[df_results['Type'] == 'Testing', 'Cumulative Return [%]'] = df_results.loc[df_results['Type'] == 'Testing', 'Return [%]'].cumsum()
        
        if len(trades_list):
            df_trades = pd.concat(trades_list, ignore_index=True)
        if len(equity_curves):
            df_equity = pd.concat(equity_curves)
        if(len(df_trades)>0):
            actual_equity_curve = (df_equity + 1).cumprod() * self.cash
            # After calculating actual_equity_curve
            # Inside the optimize function, after calculating actual_equity_curve
            if not actual_equity_curve.index.equals(data.index):
                actual_equity_curve = actual_equity_curve.reindex(data.index, method='ffill').fillna(method='bfill')
                
            actual_equity_curve = actual_equity_curve.to_frame(name = 'Equity')
            stats=compute_stats(orders=df_orders,trades=df_trades,equity=actual_equity_curve,ohlc_data=data,strategy_instance=strategy_class)

        return stats,df_results,df_trades,df_equity

    def remove_timezone(self, df):
        for col in df.select_dtypes(include=['datetimetz']).columns:
            df[col] = df[col].dt.tz_localize(None)
        return df
    
    def get_root_dir(self):
        return os.getcwd()

    def optimize_stock(self, stock, timeframe, market, exchange = None, training_candles = 2000, testing_candles = 200):
        '''
        Function to process a single stock
        '''
        stock = stock.upper()
        # First get data for the stock
        try:
            data = self.reader.fetch_stock(stock, timeframe, market, exchange)
        except Exception as e:
            print(f"Error fetching data for {stock}: {e}")
            raise
   
        # Now perform the walk forward optimisation and generate the tearsheet
        strategy_class = self.strategy
        optimization_params=self.optimization_params
        strategy_metrics = []
        data.index = data.index.tz_localize(None)
        raw_equity_curve = data['Close'].pct_change().dropna()
        raw_equity_curve.index = pd.to_datetime(raw_equity_curve.index)
        stats,df_results,df_trades,df_equity = self.optimize(strategy_class, optimization_params, data, training_candles,
                                                             testing_candles)
        
        output_root_directory = self.get_root_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_directory_path = os.path.join(output_root_directory, f'wfo_output_{timestamp}')
        self.output_directory = output_directory_path
        os.makedirs(output_directory_path)
        print("Output saved to",output_directory_path)
        
        metrics = {'Symbol': stock, 'Timeframe': timeframe}
        metrics.update(stats)
        strategy_metrics.append(metrics)
        with pd.ExcelWriter(os.path.join(output_directory_path, f'{stock}_{timeframe}.xlsx')) as writer:
            self.remove_timezone(df_results).to_excel(writer, sheet_name=timeframe)
            self.remove_timezone(df_trades).to_excel(writer, sheet_name='Trades')
            pd.DataFrame(stats).to_excel(writer,sheet_name='Summary')
        
        
        if(len(df_trades)>0):
            # print("Number of trades are: ",len(df_trades))
            df_trades.set_index('ExitTime', inplace=True)
            df_trades.index = pd.to_datetime(df_trades.index)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename=f"{stock}_{timeframe}.html"
            tear_sheet_path = os.path.join(output_directory_path, f"{filename}")
            combined_df = pd.DataFrame({
                'Benchmark': raw_equity_curve,
            })
            combined_df.index=raw_equity_curve.index
            try:
                quantstats.reports.html(df_equity, benchmark=combined_df['Benchmark'], output=tear_sheet_path)
                print(f"Tear sheet generated and saved to {tear_sheet_path}")
            except Exception as e:
                print(f"Error while generating tearsheet for {stock} {e}")
                raise
        else:
            print(f"Tradebook is empty for {stock}. Tearsheet not generated.")
            
        
    def create_tearsheets(self):
        for data_tuple in self.results:
            stock, tear_sheet_path, df_equity, benchmark = data_tuple
            try:
                quantstats.reports.html(df_equity, benchmark=benchmark, output=tear_sheet_path)
                print(f"Tear sheet generated and saved to {tear_sheet_path}")
            except Exception as e:
                print(f"Error while generating tearsheet for {stock} {e}")
                raise
        
    def process_stock_chunk(self, data_chunk):
        for data_tuple in data_chunk:
            stock, data, timeframe = data_tuple

            if len(data) == 0:
                print("No data available for stock",stock)
                continue
            
            print('WFO started for',stock)
            
            strategy_class = self.strategy
            optimization_params=self.optimization_params
            strategy_metrics = []
            data.index = data.index.tz_localize(None)
            raw_equity_curve = data['Close'].pct_change().dropna()
            raw_equity_curve.index = pd.to_datetime(raw_equity_curve.index)
            stats,df_results,df_trades,df_equity = self.optimize(strategy_class, optimization_params, data,
                                                                 self.training_candles, self.testing_candles)

            metrics = {'Symbol': stock, 'Timeframe': timeframe}
            metrics.update(stats)
            strategy_metrics.append(metrics)
            with pd.ExcelWriter(os.path.join(self.output_xl_sheets_path, f'{stock}_{timeframe}.xlsx')) as writer:
                self.remove_timezone(df_results).to_excel(writer, sheet_name=timeframe)
                self.remove_timezone(df_trades).to_excel(writer, sheet_name='Trades')
                pd.DataFrame(stats).to_excel(writer,sheet_name='Summary')
            
            print("WFO done for",stock)
            
            if(len(df_trades)>0):
                print("Number of trades are: ",stock, len(df_trades))
                df_trades.set_index('ExitTime', inplace=True)
                df_trades.index = pd.to_datetime(df_trades.index)
                filename=f"{stock}_{timeframe}.html"
                tear_sheet_path = os.path.join(self.output_tearsheets_path, filename)
                combined_df = pd.DataFrame({
                    'Benchmark': raw_equity_curve,
                })
                combined_df.index=raw_equity_curve.index
                try:
                    quantstats.reports.html(df_equity, benchmark=combined_df['Benchmark'], output=tear_sheet_path)
                    print(f"Tear sheet generated and saved to {tear_sheet_path}")
                except Exception as e:
                    print(f"Error while generating tearsheet for {stock} : {e}")
                    continue
                # return (stock, tear_sheet_path, df_equity, combined_df['Benchmark'])
            else:
                print(f"Tradebook is empty for {stock}. Tearsheet not generated.")
                # return None

    def split_list(self, data, n):
        chunk_size = math.ceil(len(data) / n)
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

    def optimize_universe(self, universe, timeframe, exchange = None, training_candles=2000, testing_candles=200):
        # First get data for the universe
        self.training_candles = training_candles
        self.testing_candles = testing_candles
        try:
            data = self.reader.fetch_universe(universe, timeframe, exchange)
        except Exception as e:
            print(f"Error fetching data for stocks for {universe}: {e}")
            raise

        print("Data fetched for",universe)

        output_root_directory = self.get_root_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_directory_path = os.path.join(output_root_directory, f'wfo_output_{timestamp}')
        self.output_directory = output_directory_path
        os.makedirs(output_directory_path)
        
        print("Output saved to",output_directory_path)
        
        os.makedirs(os.path.join(output_directory_path, 'output_xl_sheets'))
        os.makedirs(os.path.join(output_directory_path, 'output_tearsheets'))
        self.output_xl_sheets_path = os.path.join(output_directory_path, 'output_xl_sheets')
        self.output_tearsheets_path = os.path.join(output_directory_path, 'output_tearsheets')
        
        data_tuples = [(stock, stock_data, timeframe) for (stock,stock_data) in data.items()]
        data_chunks = list(self.split_list(data_tuples, self.num_processes))
        
        self.results = []
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            # Map the tasks to the stock name for later on
            futures = [executor.submit(self.process_stock_chunk, data_chunk) for data_chunk in data_chunks]
            
            for future in concurrent.futures.as_completed(futures):
                future.result() 
        
        # self.create_tearsheets()

if __name__ == "__main__":
    print("Here in main.")