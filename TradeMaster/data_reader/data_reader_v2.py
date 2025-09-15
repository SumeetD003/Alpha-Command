import requests, time,pandas as pd
from requests.auth import HTTPBasicAuth

class DataReader:
    def __init__(self):
        # Initialize the endpoint as None, will be set in the initialize method
        self.username = None

    def initialize(self, host, port, https, username, password):
        # This function will initialize the connection to the QuestDB
        self.providers={
            "indian": [("zerodha","zerodha")],
            "us": [("firstratedata","firstratedata"),("thetadata","thetadata"),("polygon","XNAS")],
            "crypto": [("binance","binance"),("firstratedata","firstratedata"),("bybit","bybit")],
            "forex": [("firstratedata","firstratedata"),("metaquotes","metaquotes")]
        }
        self.default_exchanges = {
            "indian" : "zerodha",
            "us" : "thetadata",
            "crypto" : "binance",
            "forex" : "metaquotes"
        }
        self.username = username
        if https == True:
            self.host = f"https://{host}:{port}"
        else:
            self.host = f"http://{host}:{port}"
        self.port = port
        self.password = password

    def fetch_stock(self, stock_name, timeframe, market_name, exchange_name = None):
        # Given a single stock name, this function will fetch data for the stock from given exchange, and all 
        # possible exchanges in case the exchange is omitted 
        if self.username is None:
            raise ValueError("Database connection is not initialized. Call initialize() first.")
        provider_list = self.providers[market_name.lower()]
        if exchange_name is None:
            exchange_name = self.default_exchanges[market_name]
        first_letter = stock_name[0]
        data_list = []

        for provider, exchange in provider_list:
            if exchange.lower() != exchange_name.lower():
                continue
            if market_name == "indian" or market_name == "us":
                dataset_name = f"ohlc_{market_name}_stocks_{provider}_{timeframe}_{first_letter.lower()}"
            else:
                dataset_name = f"ohlc_{market_name}_{provider}_{timeframe}_{first_letter.lower()}"
            try:
                query = f"select * from {dataset_name} where ticker='{stock_name.upper()}'"
                # print(query)
                st = time.time()
                response = requests.get(f"{self.host}/exec", params={"query": query}, auth=HTTPBasicAuth(self.username, self.password)
                            )   
                et = time.time()
                if response.status_code == 200:
                    # Convert response to pandas DataFrame
                    data = response.json()
                    columns = [col["name"] for col in data["columns"]]
                    df = pd.DataFrame(data["dataset"], columns=columns)
                    # print(df)
                    if len(df) == 0:
                        continue
                    df = df[["open", "high", "low", "close", "volume", "timestamp"]]
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df['timestamp'] = df['timestamp'].dt.tz_localize(None)
                    df.columns = df.columns.str.capitalize()
                    data_list.append(df)

                else:
                    print(f"Error: {response.status_code}, {response.text}")
                
                
            except Exception as e:
                if "table does not exist" not in str(e).lower():
                    print(f"Exception while fetching {stock_name}: {e}")
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
    
    def fetch_stocks(self, universe_name):
        query = f"select market, stocks from universe_table where universe_name = '{ universe_name }'"
        response = requests.get(f"{self.host}/exec", params={"query": query}, auth=HTTPBasicAuth(self.username, self.password)
                            )   
        if response.status_code == 200:
            data = response.json()
            data = data['dataset']
            market = data[0][0].lower()
            stocks = data[0][1].split(',')
            return (stocks,market)
        else:
            print(f"Error: {response.status_code}, {response.text}")

# Example usage
if __name__ == "__main__":
    # Create the DataReader object
    reader = DataReader()

    # Initialize the database connection with the credentials
    reader.initialize(host='qdb.satyvm.com', port=443, https = True, username='2Cents', password='2Cents$101')

    start_time = time.time()
    # result = reader.fetch_stocks("Nifty 50")
    result = reader.fetch_stock('AAPL', '1day', 'us', 'firstratedata') 
    print(result.index)
    # result = reader.fetch_stocks("S&P 500")
    # result = reader.fetch_table("indian", "1day", "a")

    end_time = time.time()
    print(f"Elapsed time: { end_time - start_time }")
    with open('output.txt', 'w') as file:
        print(result, file = file)
    

