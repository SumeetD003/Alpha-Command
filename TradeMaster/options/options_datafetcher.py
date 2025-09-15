import asyncio
import sys
import pandas as pd
from questdb_query import numpy_query, Endpoint

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class OptionsDataFetcher:
    def __init__(self, endpoint):
        """
        Initializes the data fetcher with the QuestDB REST API endpoint.
        """
        self.endpoint = endpoint

    def fetch_contracts_by_index(self, index_name):
        """
        Fetches all contracts given an index from the options symbol info table.
        """
        try:
            np_arrs = numpy_query(f"SELECT * FROM options_symbol_info WHERE index_name='{index_name}'", self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            return df
        except Exception as e:
            print(f"Error fetching contracts for index {index_name}: {e}")
            return None
    def fetch_options_ohlc(self,**kwargs):
        df=self.select_contracts(**kwargs)
        print(df)
        table_name=df['table_name'][0]
        ticker=df['ticker'][0]
        print(ticker,table_name)
        df=self.fetch_ohlc_with_greeks(ticker,table_name)
        return df

    def select_contracts(self, index=None,expiry_date=None, Time_to_expiry=None, strike_price=None, instrument_type=None,ticker=None):
        """
        Fetches contracts matching conditions (expiry date, time to expiry, strike price, instrument type).
        Filters based on the provided conditions (can use any or all).
        """
        try:
            query = "SELECT * FROM options_symbol_info WHERE 1=1"
            if ticker:
                query += f" AND ticker='{ticker}'"
            if index:
                query += f" AND index_name='{index}'"
            if expiry_date:
                query += f" AND expiry_date='{expiry_date}'"
            if Time_to_expiry:
                query += f" AND time_to_expiry={Time_to_expiry}"
            if strike_price:
                query += f" AND strike_price={strike_price}"
            if instrument_type:
                query += f" AND instrument_type='{instrument_type}'"

            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            return df
            
        except Exception as e:
            print(f"Error fetching contracts with conditions: {e}")
            return None
    def fetch_contracts(self,table_name="options_symbol_info", index=None,start_date=None, end_date = None,expiry_date= None,Time_to_expiry=None, strike_price=None, instrument_type=None):
        """
        Fetches contracts matching conditions (expiry date, time to expiry, strike price, instrument type).
        Filters based on the provided conditions (can use any or all).
        """
        try:
            query = f"SELECT * FROM {table_name} WHERE 1=1"
            if index:
                #query += f" AND index_name='{index}'"
                query += f" AND index_name='{index}'"
            if expiry_date:
                query += f" AND expiry_date='{expiry_date}'"
            if Time_to_expiry:
                query += f" AND time_to_expiry={Time_to_expiry}"
            if strike_price:
                query += f" AND strike_price={strike_price}"
            if instrument_type:
                query += f" AND instrument_type='{instrument_type}'"

            # Add expiry date range condition if provided
            if start_date is not None and end_date is not None:
                query += f" AND timestamp BETWEEN '{start_date}' AND '{end_date}'"
            elif start_date is not None:
                query += f" AND timestamp >= '{start_date}'"
            elif end_date is not None:
                query += f" AND timestamp <= '{end_date}'"    
            print(query)
            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            return df
            
        except Exception as e:
            print(f"Error fetching contracts with conditions: {e}")
            return None
    def fetch_active_contracts(self,table_name="options_symbol_info", index=None,start_date=None, end_date = None,expiry_date= None,Time_to_expiry=None, strike_price=None, instrument_type=None):
        """
        Fetches contracts matching conditions (expiry date, time to expiry, strike price, instrument type).
        Filters based on the provided conditions (can use any or all).
        """
        try:
            query = f"SELECT * FROM {table_name} WHERE 1=1"
            if index:
                #query += f" AND index_name='{index}'"
                query += f" AND index_name='{index}'"
            if expiry_date:
                query += f" AND expiry_date='{expiry_date}'"
            if Time_to_expiry:
                query += f" AND time_to_expiry={Time_to_expiry}"
            if strike_price:
                query += f" AND strike_price={strike_price}"
            if instrument_type:
                query += f" AND instrument_type='{instrument_type}'"

            # Add expiry date range condition if provided
            if start_date is not None and end_date is not None:
                query += f" AND expiry_date BETWEEN '{start_date}' AND '{end_date}'"
            elif start_date is not None:
                query += f" AND expiry_date >= '{start_date}'"
            elif end_date is not None:
                query += f" AND expiry_date <= '{end_date}'"    
            print(query)
            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            return df
            
        except Exception as e:
            print(f"Error fetching contracts with conditions: {e}")
            return None
    def fetch_ohlc_for_contracts(self, ticker, table_name):
        """
        Fetches OHLC data for contracts from the `ohlc_options_indian_nse_banknifty_6` table.
        """
        try:
            query = f"SELECT * FROM {table_name} WHERE ticker='{ticker}'"
            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            return df
        except Exception as e:
            print(f"Error fetching OHLC data for ticker {ticker}: {e}")
            return None
    def fetch_single_ohlc_with_greeks(self, ticker, table_name, timestamp):
        """
        Fetches OHLC data with Greeks for a contract at a specific timestamp.
        """
        try:
            query = f"SELECT * FROM {table_name} WHERE ticker='{ticker}' AND timestamp>'{timestamp}' AND timestamp<'{pd.Timestamp(timestamp + pd.Timedelta(minutes=1))}'"
            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            return df
        except Exception as e:
            print(f"Error fetching OHLC data with Greeks for ticker {ticker}: {e}")
            return None
    def fetch_ohlc_with_greeks(self, ticker, table_name):
        """
        Fetches OHLC data with Greeks for a contract at a specific timestamp.
        """
        try:
            query = f"SELECT * FROM {table_name} WHERE ticker='{ticker}'"
            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume':'Volume'
            }, inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching OHLC data with Greeks for ticker {ticker}: {e}")
            return None
    def add_ohlc_with_greeks_to_active_contracts(self, active_contracts_df, timestamp):
        print("timestamp is",timestamp)
        all_rows = []  # List to hold all new rows

        for index, row in active_contracts_df.iterrows():
            ticker = row['ticker']
            table_name = row['table_name']
            ohlc_with_greeks_data = self.fetch_single_ohlc_with_greeks(ticker, table_name, timestamp)
            
            if ohlc_with_greeks_data is not None:
                all_rows.append(ohlc_with_greeks_data)  # Add the new data to the list

        if all_rows:
            # Concatenate new rows to the original DataFrame
            new_data_df = pd.concat(all_rows)
            #active_contracts_df = pd.concat([active_contracts_df, new_data_df], ignore_index=True)
            #active_contracts_df.dropna(inplace=True)
        return new_data_df
    def get_contract_by_delta(self,contracts_df, target_delta):
        print(contracts_df)
        contracts_df.to_csv("contracts.csv")
        """
        Fetches the contract with the closest delta to the target delta.

        Parameters:
        contracts_df (pd.DataFrame): DataFrame containing the options contracts.
        target_delta (float): The target delta to match (e.g., 0.5).

        Returns:
        pd.Series: The row of the DataFrame corresponding to the contract with the closest delta.
        """
        # Ensure the 'delta' column exists in the DataFrame
        if 'delta' not in contracts_df.columns:
            raise ValueError("The provided DataFrame does not have a 'delta' column.")

        # Find the contract with the closest delta to the target delta
        closest_contract = contracts_df.iloc[(contracts_df['delta'] - target_delta).abs().idxmin()]
        
        return closest_contract
    def fetch_options_chain(self):
        try:
            query = f"""
                SELECT * from ohlc_Indian_NSE_banknifty_options
            """
            print(query)
            np_arrs = numpy_query(query, self.endpoint, 7)
            print(np_arrs)
            df = pd.DataFrame(np_arrs)
            print(df)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            print(df)
            df.set_index('timestamp', inplace=True)
            df = df[df.index > '2023-12-31']
            return df
        except Exception as e:
            print(f"Error fetching OHLC data for ticker: {e}")
            return None
    def fetch_spot_ohlc(self,table_name,period,ticker):
        """
        Fetches OHLC data for contracts from the `ohlc_options_indian_nse_banknifty_6` table.
        """
        try:
            query = f"""
                SELECT
                    timestamp,
                    first(open) AS Open,
                    max(high) AS High,
                    min(low) AS Low,
                    last(close) AS Close,
                    sum(volume) AS Volume
                FROM {table_name}
                WHERE ticker='{ticker}'
                SAMPLE BY {period};
            """
            print(query)
            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df = df[df.index > '2023-12-31']
            return df
        except Exception as e:
            print(f"Error fetching OHLC data for ticker {table_name}: {e}")
            return None

"""
host = '62.72.42.9'
endpoint = Endpoint(host=host, port=9000, https=False, username='admin', password='2Cents#101')
fetcher = OptionsDataFetcher(endpoint=endpoint)

matching_table_name= fetcher.fetch_contracts_with_conditions(index='BANKNIFTY',expiry_date='2016-08-25', strike_price=18000, instrument_type='PE')

# Fetch OHLC data for a contract
pd.set_option('display.max_columns', None)
spot_data = fetcher.fetch_spot_ohlc('ohlc_indian_index','1d')
print(spot_data)
ohlc_data = fetcher.fetch_ohlc_for_contracts(ticker='BANKNIFTY25AUG1618000PE', table_name=matching_table_name)
if ohlc_data is not None:
    print(ohlc_data.head())
"""
