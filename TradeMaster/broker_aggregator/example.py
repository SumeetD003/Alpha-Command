from aggregator import BrokerAggregator

aggregator = BrokerAggregator()
""""""
# Set the active broker to MT5 and connect
aggregator.set_active_broker('mt5', account_id=5026568633, password='+dBbD5Jm', server='MetaQuotes-Demo', path="C:\\Program Files\\MetaTrader 5\\terminal64.exe")

# Get balance
balance = aggregator.get_balance()
print(f"MT5 Balance: {balance}")

# Place an order
order = aggregator.place_order(symbol='EURUSD', volume=0.10, order_type='BUY')
print(f"Order placed: {order}")

## changing broker here

"""
# Set the active broker to CCXT Binance and connect
aggregator.set_active_broker('ccxt_binance_testnet', api_key='9de7f97b5ea058c06cd0da99ffe50921ddc9a0ab48ed814ffd046fbf4de56f9f', secret='84ff2355a749076426daefc81d2c4e17e6fffb1390e9d7dd10408d4ed2649f99')

# Get balance
balance = aggregator.get_balance()
print(f"Binance Balance: {balance}")

# Place an order on Binance
order = aggregator.place_order(symbol='BTC/USDT', volume=0.01, order_type='BUY', price=30000)
print(f"Order placed: {order}")

# Get order details
order_details = aggregator.get_order(order_id=order['id'], symbol='BTC/USDT')
print(f"Order details: {order_details}")

# Cancel order
cancel_result = aggregator.cancel_order(order_id=order['id'], symbol='BTC/USDT')
print(f"Order canceled: {cancel_result}")

"""