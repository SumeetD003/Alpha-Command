from concurrent.futures import ProcessPoolExecutor
import os
import traceback
import pandas as pd
from TradeMaster.backtesting import Backtest
from helpers.read_data import FTPClient

ftp_server = '82.180.146.204'
ftp_username = 'Administrator'
ftp_password = '2CentsOptions'

client = FTPClient(ftp_server, ftp_username, ftp_password)


def process_backtest(params):
    try:
        Strategy, data, symbol, timeframe, output_folder = params

        output_folder = os.path.join(output_folder, symbol)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if symbol in data and timeframe in data[symbol]:
            df = data[symbol][timeframe]
            print(f"Processing {symbol} - {timeframe}")

            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]

            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            df.sort_index()

            bt = Backtest(df, Strategy, cash=10000, commission=.002)
            stats = bt.run()

            summary_df = pd.DataFrame([stats])
            summary_df.to_csv(os.path.join(output_folder, f'{symbol}_{timeframe}_summary.csv'), index=True)
            trades_df = stats['_trades']
            trades_df.to_csv(os.path.join(output_folder, f'{symbol}_{timeframe}_trades.csv'), index=False)
            equity_df = stats['_equity_curve']
            equity_df.to_csv(os.path.join(output_folder, f'{symbol}_{timeframe}_equity.csv'), index=False)

            try:
                plot_path = os.path.join(output_folder, f'{symbol}_{timeframe}_plot.html')
                bt.plot(open_browser=False, filename=plot_path)
            except Exception as e:
                print(f"Plotting error: {e}")

            result = (
                symbol, timeframe, stats['Start'], stats['End'], stats['Duration'],
                stats['Exposure Time [%]'], stats['Equity Final [$]'], stats['Equity Peak [$]'],
                stats['Return [%]'], stats['Buy & Hold Return [%]'], stats['Return (Ann.) [%]'],
                stats['Volatility (Ann.) [%]'], stats['Sharpe Ratio'], stats['Sortino Ratio'],
                stats['Calmar Ratio'], stats['Max. Drawdown [%]'], stats['Avg. Drawdown [%]'],
                stats['Max. Drawdown Duration'], stats['Avg. Drawdown Duration'], stats['# Trades'],
                stats['Win Rate [%]'], stats['Best Trade [%]'], stats['Worst Trade [%]'],
                stats['Avg. Trade [%]'], stats['Max. Trade Duration'], stats['Avg. Trade Duration'],
                stats['Profit Factor'], stats['Expectancy [%]'], stats['SQN'], stats['Kelly Criterion']
            )
            return result
    except Exception as e:
        print(f"Error processing {params}: {e}")
        traceback.print_exc()
        return None
    
    
    
def multi_backtest(Strategy, markets, timeframes, output_csv, output_folder, exchanges = "smart"):
    results = []

    if exchanges == "smart":
        exchanges = ["NSE"] # add more exchanges as we collect more data.
        
    # markets = ['EQ']
    # exchanges = ['NSE']
    # timeframes = ['15minute', '60minute']

    all_data = {}

    try:
        for market in markets:
            for exchange in exchanges:
                all_data[exchange] = {}
                for timeframe in timeframes:
                    print(f"Fetching data for Market: {market}, Exchange: {exchange}, Timeframe: {timeframe}")
                    client.connect()
                    data = client.fetch_all_symbols_data(market, exchange, timeframe)
                    client.disconnect()
                    all_data[exchange][timeframe] = data
    finally:
        pass

    params_list = []
    for exchange, symbols_data in all_data.items():
        for symbol, timeframes_data in symbols_data.items():
            for timeframe, df in timeframes_data.items():
                params_list.append((Strategy, all_data, symbol, timeframe, output_folder))

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        for result in executor.map(process_backtest, params_list):
            if result:
                results.append(result)

    results_df = pd.DataFrame(results, columns=[
        "Asset", "Timeframe", "Start", "End", "Duration", "Exposure Time [%]", "Equity Final [$]", "Equity Peak [$]",
        "Return [%]", "Buy & Hold Return [%]", "Return (Ann.) [%]", "Volatility (Ann.) [%]", "Sharpe Ratio",
        "Sortino Ratio", "Calmar Ratio", "Max. Drawdown [%]", "Avg. Drawdown [%]", "Max. Drawdown Duration",
        "Avg. Drawdown Duration", "Number of Trades", "Win Rate [%]", "Best Trade [%]", "Worst Trade [%]",
        "Avg. Trade [%]", "Max. Trade Duration", "Avg. Trade Duration", "Profit Factor", "Expectancy [%]",
        "SQN", "Kelly Criterion"
    ])
    results_df.to_csv(output_csv, index=False)