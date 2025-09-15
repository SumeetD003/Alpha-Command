import asyncio
import sys
import pandas as pd
from questdb_query import numpy_query, Endpoint
from datetime import datetime


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

    def fetch_contracts_with_conditions(self, index=None,expiry_date= None, start_date=None, end_date = None,Time_to_expiry=None, strike_price=None, instrument_type=None):
        """
        Fetches contracts matching conditions (expiry date, time to expiry, strike price, instrument type).
        Filters based on the provided conditions (can use any or all).
        """
        try:
            query = "SELECT * FROM options_symbol_info WHERE 1=1"
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

            # Add expiry date range condition if provided
            if start_date is not None and end_date is not None:
                query += f" AND expiry_date BETWEEN '{start_date}' AND '{end_date}'"
            elif start_date is not None:
                query += f" AND expiry_date >= '{start_date}'"
            elif end_date is not None:
                query += f" AND expiry_date <= '{end_date}'"    

            np_arrs = numpy_query(query, self.endpoint, 7)
            df = pd.DataFrame(np_arrs)
            return df['table_name'].tolist()
            
        except Exception as e:
            print(f"Error fetching contracts with conditions: {e}")
            return None

    def fetch_ohlc_for_contracts(self,table_names, iv_min=None, iv_max=None, delta_min=None, delta_max=None,
                             gamma_min=None, gamma_max=None, vega_min=None, vega_max=None, theta_min=None, theta_max=None,
                             rho_min=None, rho_max=None, start_timestamp=None, end_timestamp=None, date_column='date'):
        """
    Fetches OHLC data for contracts from the specified table filtered by IV, delta, gamma, vega, theta, rho, and date range.
    
    Parameters:
        ticker (str): Ticker symbol.
        table_name (str): Database table name.
        iv_min (float, optional): Minimum implied volatility.
        iv_max (float, optional): Maximum implied volatility.
        delta_min (float, optional): Minimum delta.
        delta_max (float, optional): Maximum delta.
        gamma_min (float, optional): Minimum gamma.
        gamma_max (float, optional): Maximum gamma.
        vega_min (float, optional): Minimum vega.
        vega_max (float, optional): Maximum vega.
        theta_min (float, optional): Minimum theta.
        theta_max (float, optional): Maximum theta.
        rho_min (float, optional): Minimum rho.
        rho_max (float, optional): Maximum rho.
        start_date (datetime.date, optional): Start date for filtering.
        end_date (datetime.date, optional): End date for filtering.
        date_column (str): The name of the date column in the table (default is 'date')."""
        
        try:
            if start_timestamp is not None:
                start_timestamp = datetime.strptime(start_timestamp, '%Y-%m-%d %H:%M')
        
            if end_timestamp is not None:
                end_timestamp = datetime.strptime(end_timestamp, '%Y-%m-%d %H:%M')
            all_data_frames = []
            for table_name in table_names:
                query = f"SELECT * FROM {table_name} WHERE 1=1"
                if iv_min is not None:
                    query += f" AND iv >= {iv_min}"
            
                if iv_max is not None:
                    query += f" AND iv <= {iv_max}"

                if delta_min is not None:
                    query += f" AND delta >= {delta_min}"

                if delta_max is not None:
                    query += f" AND delta <= {delta_max}"
        
                if gamma_min is not None:
                    query += f" AND gamma >= {gamma_min}"

                if gamma_max is not None:
                    query += f" AND gamma <= {gamma_max}"
        
                if vega_min is not None:
                    query += f" AND vega >= {vega_min}"

                if vega_max is not None:
                    query += f" AND vega <= {vega_max}"
        
                if theta_min is not None:
                    query += f" AND theta >= {theta_min}"

                if theta_max is not None:
                    query += f" AND theta <= {theta_max}"
        
                if rho_min is not None:
                    query += f" AND rho >= {rho_min}"

                if rho_max is not None:
                    query += f" AND rho <= {rho_max}"

        
                if start_timestamp is not None:
                    start_date_str = start_timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    query += f" AND {date_column} >= '{start_date_str}'"

                if end_timestamp is not None:
                    end_date_str = end_timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    query += f" AND {date_column} <= '{end_date_str}'"

        
                np_arrs = numpy_query(query, self.endpoint, 7)
                df = pd.DataFrame(np_arrs)
                if not df.empty:
                    all_data_frames.append(df)
                return df
    
        except Exception as e:
            print(f"Error fetching OHLC data for ticker: {e}")
            return None
    
    
    
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# Example Usage:
host = '62.72.42.9'
endpoint = Endpoint(host=host, port=9000, https=False, username='admin', password='2Cents#101')
fetcher = OptionsDataFetcher(endpoint=endpoint)
# Fetch all contracts for a specific index
#contracts_for_nifty = fetcher.fetch_contracts_by_index(index_name="BANKNIFTY")
#if contracts_for_nifty is not None:
    #print(contracts_for_nifty.head())

# Fetch contracts matching conditions (expiry date, time to expiry, strike price, instrument type)
matching_table_names= fetcher.fetch_contracts_with_conditions(index='BANKNIFTY', start_date='2016-06-02', end_date='2016-08-25')
#if matching_table_names is not None:
    #print(matching_table_names)
   

# Fetch OHLC data for a contract
pd.set_option('display.max_columns', None)
ohlc_data = fetcher.fetch_ohlc_for_contracts(table_names=matching_table_names, delta_max=-0.05, delta_min=-0.09)
if ohlc_data is not None:
    print(ohlc_data.head())