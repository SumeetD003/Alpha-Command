import pandas as pd
from questdb_query import pandas_query, Endpoint, numpy_query

class DataReader:
    def __init__(self):
        # Initialize the endpoint as None, will be set in the initialize method
        self.endpoint = None

    def initialize(self, host, port, username, password):
        # This function will initialize the connection to the QuestDB
        self.endpoint = Endpoint(host=host, port=port, https=False, username=username, password=password)
        print("Database connection initialized.")

    def get_symbol_info(self, symbol_name, exchange, market):
        # Ensure the database connection is initialized
        if self.endpoint is None:
            raise ValueError("Database connection is not initialized. Call initialize() first.")
        
        # Query to fetch symbol_id and table_name based on the input parameters
        query = f"""
            SELECT symbol_id, table_name
            FROM symbol_info 
            WHERE name = '{symbol_name}' AND exchange = '{exchange}' AND market = '{market}'
        """
        result = pandas_query(query, self.endpoint)
        if result.empty:
            raise ValueError("No data found for the given symbol, exchange, and market.")
        
        symbol_id = result['symbol_id'].iloc[0]
        table_name = result['table_name'].iloc[0]
        print(symbol_id,table_name,result)
        return symbol_id, table_name
    def get_data(self, symbol_name, exchange, market):
        symbol_id, table_name = reader.get_symbol_info(symbol_name, exchange, market)
        print(f"Symbol ID: {symbol_id}, Table Name: {table_name}")
        data = reader._fetch_symbol_data(symbol_id, table_name)
        return data
    def _fetch_symbol_data(self, symbol_id, table_name):
        if self.endpoint is None:
            raise ValueError("Database connection is not initialized. Call initialize() first.")
        
        # Query to fetch all data from the table corresponding to the symbol_id and table_name
        query = f"""
            SELECT * 
            FROM {table_name} 
            WHERE symbol_id = {symbol_id}
        """
        data = pandas_query(query, self.endpoint)
        return data

# Example usage
if __name__ == "__main__":
    # Create the DataReader object
    reader = DataReader()

    # Initialize the database connection with the credentials
    reader.initialize(host='62.72.42.9', port=9000, username='admin', password='2Cents#101')

    # Example input symbol
    symbol_name = '1INCHUSDT'
    exchange = 'Binance'
    market = 'Crypto'

    # Get the symbol_id and table_name from symbol_info table
    
    data=reader.get_data(symbol_name,exchange,market)
    print(data)