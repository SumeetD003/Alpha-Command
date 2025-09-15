import os
from questdb_query.asynchronous import pandas_query 
from questdb_query import Endpoint
import pandas as pd
import time, sys, asyncio, nest_asyncio, json, os
from concurrent.futures import ProcessPoolExecutor

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
nest_asyncio.apply()

class DataReader:
    def __init__(self):
        # Initialize the endpoint as None, will be set in the initialize method
        self.endpoint = None

    def initialize(self, host, port, https,  username, password):
        # This function will initialize the connection to the QuestDB
        self.providers={
            "indian": [("zerodha","zerodha")],
            "us": [("firstratedata","firstratedata"),("thetadata","thetadata"),("polygon","XNAS")],
            "crypto": [("binance","binance"),("firstratedata","firstratedata"),("bybit","bybit")],
            "forex": [("firstratedata","firstratedata"),("metaquotes","metaquotes")]
        }

        trademaster_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.abspath(os.path.join(trademaster_dir, '..'))
        storage_dir = os.path.join(parent_dir, 'storage')
        default_exchanges_path = os.path.join(storage_dir, 'default_exchanges.json')
        timeframes_path = os.path.join(storage_dir, 'timeframes.json')
        market_map_path = os.path.join(storage_dir, 'stock_market_mapping.json')
        with open(default_exchanges_path, 'r') as file:
            self.default_exchanges = json.load(file)
        with open(timeframes_path, 'r') as file:
            self.timeframes = json.load(file)
        with open(market_map_path, 'r') as file:
            self.market_map = json.load(file)
        try:
            self.endpoint = Endpoint(host=host, port=port, https=https, username=username, password=password)
            print("Database connection initialized.")
        except Exception as e:
            print(f"Error connecting: {e}")

    async def fetch_single_stock(self, data_tuple):
        stock_name, timeframe, market_name, exchange_name = data_tuple
        # Given a single stock name, this function will fetch data for the stock from given exchange, and all 
        # possible exchanges in case the exchange is omitted 
        if self.endpoint is None:
            raise ValueError("Database connection is not initialized. Call initialize() first.")
        
        if market_name.lower() == 'all': # Only in benchmarking
            market_name = self.market_map[stock_name.upper()]
            exchange_name = None
        
        provider_list = self.providers[market_name.lower()]
        if exchange_name is None:
            exchange_name = self.default_exchanges[market_name]
        first_letter = stock_name[0].lower()
        data_list = []

        for provider, exchange in provider_list:
            if exchange.lower() != exchange_name.lower():
                continue
            if market_name == "indian" or market_name == "us":
                dataset_name = f"ohlc_{market_name}_stocks_{provider}_{timeframe}_{first_letter}_partition_by_year"
            else:
                dataset_name = f"ohlc_{market_name}_{provider}_{timeframe}_{first_letter}_partition_by_year"
            try:
                query = f"select open, high, low, close, volume, timestamp from {dataset_name} where ticker='{stock_name.upper()}'"
                df = await pandas_query(query, self.endpoint)
                # print(f"Data fetched for {stock_name} in {df.query_stats.duration_s}")
                if len(df) == 0:
                    continue
                df.columns = df.columns.str.capitalize()
                data_list.append(df)
            except Exception as e:
                if "table does not exist" not in str(e).lower():
                        # print(f"Exception while fetching {stock_name}: {e}")
                    raise
                continue
            
        if data_list:
            df = pd.concat(data_list, axis=0)
            df.set_index("Timestamp", inplace = True)
            df = df.loc[~df.index.duplicated(keep='first')]
            return df
        else:
            df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume", "Timestamp"]) # Empty dataframe
            df.set_index("Timestamp", inplace = True)
            return df
        
    def fetch_single_stock_with_name(self, data_tuple):
        """
        A helper function to fetch the stock data and pair it with the stock name.
        This avoids using lambda in multiprocessing (which can't be pickled).
        """
        stock_name = data_tuple[0]
        data_frame = asyncio.run(self.fetch_single_stock(data_tuple))
        return (stock_name, data_frame)    
    
    def fetch_single_stock_with_timeframe(self, data_tuple):
        """
        A helper function to fetch the stock data and pair it with the timeframe.
        This avoids using lambda in multiprocessing (which can't be pickled).
        """
        timeframe = data_tuple[1]
        data_frame = asyncio.run(self.fetch_single_stock(data_tuple))
        return (timeframe, data_frame) 
    
    def fetch_single_stock_with_name_and_timeframe(self, data_tuple):
        """
        A helper function to fetch the stock data and pair it with the name and timeframe.
        This avoids using lambda in multiprocessing (which can't be pickled).
        """
        stock = data_tuple[0]
        timeframe = data_tuple[1]
        data_frame = asyncio.run(self.fetch_single_stock(data_tuple))
        return (stock, timeframe, data_frame)   
        
    def fetch_stock(self, stock_name, timeframe, market_name, exchange_name = None):
        if self.endpoint is None:
            raise ValueError("Database connection is not initialized. Call initialize() first.")
        data_tuple = (stock_name, timeframe, market_name, exchange_name)
        result = asyncio.run(self.fetch_single_stock(data_tuple))
        return result

    async def universal_dataset_reader(self, universe_name, timeframe, exchange_name=None):
        df = await pandas_query(f"select * from universe_table where universe_name='{universe_name}'", self.endpoint)
        df = df.iloc[0]
        market = df['market'].lower()
        if market == "all": # For benchmarking only
            exchange_name = 'all'
        stocks = [ s.lower() for s in df['stocks'].split(',') ]
        if exchange_name is None:
            exchange_name = self.default_exchanges[market]
        result_dict = {}
        data_tuples = [(stock, timeframe, market, exchange_name) for stock in stocks]
        results = []
        with ProcessPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.fetch_single_stock_with_name, data) for data in data_tuples]
            for future in futures:
                t = future.result()
                results.append(t)
    
        for (stock,data) in results:
            result_dict[stock] = data
        return result_dict

    def fetch_universe(self, universe_name, timeframe, exchange_name = None):
        # Given a universe name and time frame, this function will return data for all stocks in that
        # universe and exchange, consider default exchanges in case exchange name is omitted
        if self.endpoint is None:
            raise ValueError("Database connection is not initialized. Call initialize() first.")
        result = asyncio.run(self.universal_dataset_reader(universe_name, timeframe, exchange_name))
        return result
    
    async def get_stocks(self, universe_name):
        df = await pandas_query(f"select * from universe_table where universe_name = '{ universe_name }'", self.endpoint)
        df = df.iloc[0]
        return ( df['stocks'].split(',') , df['market'].lower() )
    
    def fetch_stocks(self, universe_name):
        return asyncio.run(self.get_stocks(universe_name))
    
    async def get_stock_alltfs(self, stock, market, exchange):
        market = market.lower()
        # print(market)
        if market == 'all': # Only for benchmarking
            market = self.market_map[stock]
            exchange = self.default_exchanges[market]
        if exchange is None:
            exchange = self.default_exchanges[market]
        result_dict = {}
        data_tuples = [(stock, timeframe, market, exchange) for timeframe in self.timeframes]
        results = []
        with ProcessPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.fetch_single_stock_with_timeframe, data) for data in data_tuples]
            for future in futures:
                t = future.result()
                results.append(t)
    
        for (timeframe,data) in results:
            if len(data):
                result_dict[timeframe] = data
            
        return result_dict
    
    def fetch_stock_alltfs(self, stock, market, exchange = None):
        # Given a stock name, this function will return data for all timeframes for this stock.
        if self.endpoint is None:
            raise ValueError("Database connection is not initialized. Call initialize() first.")
        result = asyncio.run(self.get_stock_alltfs(stock, market, exchange))
        return result

# Example usage
if __name__ == "__main__":
    # Create the DataReader object
    reader = DataReader()

    # Initialize the database connection with the credentials
    reader.initialize(host='qdb.satyvm.com', port=443, https=True, username='2Cents', password='2Cents$1012cc')

    start_time = time.time()
    # result = reader.fetch_stocks("Nifty 50")
    # result = reader.fetch_stock('AAPL', '1min', 'us', 'firstratedata') 
    result = reader.fetch_universe("Benchmark5","1day","All")
    # result = reader.fetch_table("indian", "1day", "a")
    # result = reader.fetch_stock_alltfs('A', 'us', 'firstratedata')

    end_time = time.time()
    print(f"Elapsed time: { end_time - start_time }")
    with open('output.txt', 'w') as file:
        print(result, file = file)
    

