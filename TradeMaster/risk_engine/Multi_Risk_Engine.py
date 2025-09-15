import os
import sys
import math
import pandas as pd
from datetime import datetime
import pandas_ta as ta

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from TradeMaster.backtesting import Strategy, Order, Trade

class MultiTpSlModel:
    def __init__(self, strategy):
        self.strategy = strategy
        self.active_trades = {}

    def setup_trade(self, trade_id, trade_info, trade):
        """Set up TP/SL orders and initialize active trade state."""
        qty = trade_info['quantity']
        entry_price = trade_info['entry_price']
        entry_time = trade_info['entry_time']
        weighted_tp = trade_info['tp_levels']
        weighted_sl = trade_info['sl_levels']
        tp_levels = trade_info['tp_levels_list']
        sl_levels = trade_info['sl_levels_list']
        tp_weights = trade_info['tp_weights']
        sl_weights = trade_info['sl_weights']
        is_long = trade_info['direction'] == 'buy'

        # Initialize or update active trade state
        self.active_trades[trade_id] = {
            'sl_levels': weighted_sl,
            'tp_levels': weighted_tp,
            'initial_qty': qty,
            'remaining_size': qty,
            'is_long': is_long,
            'tp_weights': tp_weights,
            'sl_weights': sl_weights
        }
        self.strategy.active_trades[trade_id] = self.active_trades[trade_id]  # Sync with strategy

        remaining_size = qty
        for i, (tp_price, tp_weight) in enumerate(zip(tp_levels, tp_weights)):
            close_size = int(tp_weight * qty) if i == 0 else int(tp_weight / sum(tp_weights[i:]) * remaining_size)
            remaining_size -= close_size
            if close_size == 0 and remaining_size > 0:
                close_size = 1
            if close_size > 0:
                limit_order = Order(
                    broker=self.strategy._broker,
                    ticker=self.strategy.data.tickers[0] if isinstance(self.strategy.data.tickers, list) else self.strategy.data.tickers,
                    size=-close_size if is_long else close_size,
                    limit_price=tp_price,
                    parent_trade=trade,
                    entry_time=entry_time,
                    tag=f"TP_{trade_id}_{tp_price}"
                )
                self.strategy._broker.orders.insert(0, limit_order)
                self.strategy.active_orders[trade_id]['tp'].append(limit_order)
                print(f"Created TP order: Trade {trade_id}, Price = {tp_price}, Size = {close_size}")

        remaining_size = qty
        for i, (sl_price, sl_weight) in enumerate(zip(sl_levels, sl_weights)):
            close_size = int(sl_weight * qty) if i == 0 else int(sl_weight / sum(sl_weights[i:]) * remaining_size)
            remaining_size -= close_size
            if close_size == 0 and remaining_size > 0:
                close_size = 1
            if close_size > 0:
                stop_order = Order(
                    broker=self.strategy._broker,
                    ticker=self.strategy.data.tickers[0] if isinstance(self.strategy.data.tickers, list) else self.strategy.data.tickers,
                    size=-close_size if is_long else close_size,
                    stop_price=sl_price,
                    parent_trade=trade,
                    entry_time=entry_time,
                    tag=f"SL_{trade_id}_{sl_price}"
                )
                self.strategy._broker.orders.insert(0, stop_order)
                self.strategy.active_orders[trade_id]['sl'].append(stop_order)
                print(f"Created SL order: Trade {trade_id}, Price = {sl_price}, Size = {close_size}")
    def process(self, trade_id, trade_info, current_price, current_time):
        """Process Multi TP/SL exits and adjust orders for the MultiTpSlModel."""
        if trade_info['remaining_size'] <= 0:
            return
        entry_price = self.strategy.trade_details[trade_id]['entry_price']
        is_long = trade_info['is_long']
        initial_qty = trade_info['initial_qty']
        total_exited = initial_qty - trade_info['remaining_size']

        print(f"Trade {trade_id}: Remaining Size = {trade_info['remaining_size']}, TP Levels = {trade_info['tp_levels']}, SL Levels = {trade_info['sl_levels']}, Current Price = {current_price}")

        # Check for executed TP orders
        executed_tp_orders = []
        for order in self.strategy.active_orders[trade_id]['tp'][:]:
            if order not in self.strategy._broker.orders:
                executed_tp_orders.append(order)
                self.strategy.active_orders[trade_id]['tp'].remove(order)
            else:
                break

        # Process all executed TP orders in this bar
        executed_tp_orders = sorted(executed_tp_orders, key=lambda x: float(x.tag.split('_')[-1]))
        for order in executed_tp_orders:
            order_type, order_trade_id, order_price = order.tag.split('_')
            order_price = float(order_price)
            
            booked_levels = [entry['price'] for entry in self.strategy.trade_details[trade_id]['booked']]
            if order_price in booked_levels:
                continue
            
            close_size = abs(order.size)
            close_size = min(close_size, trade_info['remaining_size'])  # Cap close_size to prevent negative remaining_size
            if close_size > 0:
                trade_info['remaining_size'] -= close_size
                total_exited += close_size
                pnl = self.strategy.calculate_pnl(entry_price, order_price, close_size, is_long)
                position_value = trade_info['remaining_size'] * current_price
                cash_after = (self.strategy._broker._cash - position_value) + pnl

                print(f"Trade {trade_id} (TP Exit): Close Size = {close_size}, Exit Price = {order_price}, PnL = {pnl}, Is Long = {is_long}")

                self.strategy.tradebook[trade_id]['exits'].append({
                    'price': order_price,
                    'size': close_size,
                    'time': current_time,
                    'type': 'tp',
                    'pnl': pnl,
                    'cash_after': cash_after,
                    'remaining_qty': trade_info['remaining_size'],
                    'position_value': position_value
                })
                self.strategy.trade_details[trade_id]['booked'].append({
                    'price': order_price,
                    'size': close_size,
                    'type': 'tp'
                })

                # Adjust SL order sizes based on the new remaining size, but only if remaining_size > 0
                if trade_info['remaining_size'] > 0:
                    remaining_sl_levels = []
                    remaining_sl_weights = []
                    for sl_order in self.strategy.active_orders[trade_id]['sl']:
                        _, _, sl_price = sl_order.tag.split('_')
                        sl_price = float(sl_price)
                        if sl_price not in booked_levels:
                            remaining_sl_levels.append(sl_price)
                            for i, sl_dict in enumerate(trade_info['sl_levels']):
                                if float(next(iter(sl_dict))) == sl_price:
                                    remaining_sl_weights.append(trade_info['sl_weights'][i])
                                    break

                    # Remove existing SL orders
                    for sl_order in self.strategy.active_orders[trade_id]['sl']:
                        if sl_order in self.strategy._broker.orders:
                            self.strategy._broker.orders.remove(sl_order)
                    self.strategy.active_orders[trade_id]['sl'] = []

                    # Recreate SL orders with updated sizes
                    remaining_size_for_sl = trade_info['remaining_size']
                    for i, (sl_price, sl_weight) in enumerate(zip(remaining_sl_levels, remaining_sl_weights)):
                        close_size = int(sl_weight / sum(remaining_sl_weights[i:]) * remaining_size_for_sl) if sum(remaining_sl_weights[i:]) > 0 else remaining_size_for_sl
                        close_size = min(close_size, trade_info['remaining_size'])  # Cap close_size
                        remaining_size_for_sl -= close_size
                        if close_size == 0 and remaining_size_for_sl > 0:
                            close_size = 1  # Ensure non-zero size
                        if close_size > 0:  # Only create order if size is non-zero
                            stop_order = Order(
                                broker=self.strategy._broker,
                                ticker=self.strategy.data.tickers[0] if isinstance(self.strategy.data.tickers, list) else self.strategy.data.tickers,
                                size=-close_size if is_long else close_size,
                                stop_price=sl_price,
                                parent_trade=self.strategy.trade_mapping[trade_id],
                                entry_time=self.strategy.tradebook[trade_id]['entry_time'],
                                tag=f"SL_{trade_id}_{sl_price}"
                            )
                            self.strategy._broker.orders.insert(0, stop_order)
                            self.strategy.active_orders[trade_id]['sl'].append(stop_order)

        # Check for executed SL orders
        if trade_id in self.active_trades:
            executed_sl_orders = []
            for order in self.strategy.active_orders[trade_id]['sl'][:]:
                if order not in self.strategy._broker.orders:
                    executed_sl_orders.append(order)
                    self.strategy.active_orders[trade_id]['sl'].remove(order)
                else:
                    break

            executed_sl_orders = sorted(executed_sl_orders, key=lambda x: float(x.tag.split('_')[-1]), reverse=True)
            for order in executed_sl_orders:
                order_type, order_trade_id, order_price = order.tag.split('_')
                order_price = float(order_price)
                
                booked_levels = [entry['price'] for entry in self.strategy.trade_details[trade_id]['booked']]
                if order_price in booked_levels:
                    continue
                
                close_size = abs(order.size)
                close_size = min(close_size, trade_info['remaining_size'])  # Cap close_size to prevent negative remaining_size
                if close_size > 0:
                    trade_info['remaining_size'] -= close_size
                    total_exited += close_size
                    pnl = self.strategy.calculate_pnl(entry_price, order_price, close_size, is_long)
                    position_value = trade_info['remaining_size'] * current_price
                    cash_after = (self.strategy._broker._cash - position_value) + pnl

                    print(f"Trade {trade_id} (SL Exit): Close Size = {close_size}, Exit Price = {order_price}, PnL = {pnl}, Is Long = {is_long}")

                    self.strategy.tradebook[trade_id]['exits'].append({
                        'price': order_price,
                        'size': close_size,
                        'time': current_time,
                        'type': 'sl',
                        'pnl': pnl,
                        'cash_after': cash_after,
                        'remaining_qty': trade_info['remaining_size'],
                        'position_value': position_value
                    })
                    self.strategy.trade_details[trade_id]['booked'].append({
                        'price': order_price,
                        'size': close_size,
                        'type': 'sl'
                    })

                    # Adjust TP order sizes based on the new remaining size, but only if remaining_size > 0
                    if trade_info['remaining_size'] > 0:
                        remaining_tp_levels = []
                        remaining_tp_weights = []
                        for tp_order in self.strategy.active_orders[trade_id]['tp']:
                            _, _, tp_price = tp_order.tag.split('_')
                            tp_price = float(tp_price)
                            if tp_price not in booked_levels:
                                remaining_tp_levels.append(tp_price)
                                for i, tp_dict in enumerate(trade_info['tp_levels']):
                                    if float(next(iter(tp_dict))) == tp_price:
                                        remaining_tp_weights.append(trade_info['tp_weights'][i])
                                        break

                        # Remove existing TP orders
                        for tp_order in self.strategy.active_orders[trade_id]['tp']:
                            if tp_order in self.strategy._broker.orders:
                                self.strategy._broker.orders.remove(tp_order)
                        self.strategy.active_orders[trade_id]['tp'] = []

                        # Recreate TP orders with updated sizes
                        remaining_size_for_tp = trade_info['remaining_size']
                        for i, (tp_price, tp_weight) in enumerate(zip(remaining_tp_levels, remaining_tp_weights)):
                            close_size = int(tp_weight / sum(remaining_tp_weights[i:]) * remaining_size_for_tp) if sum(remaining_tp_weights[i:]) > 0 else remaining_size_for_tp
                            close_size = min(close_size, trade_info['remaining_size'])  # Cap close_size
                            remaining_size_for_tp -= close_size
                            if close_size == 0 and remaining_size_for_tp > 0:
                                close_size = 1  # Ensure non-zero size
                            if close_size > 0:  # Only create order if size is non-zero
                                limit_order = Order(
                                    broker=self.strategy._broker,
                                    ticker=self.strategy.data.tickers[0] if isinstance(self.strategy.data.tickers, list) else self.strategy.data.tickers,
                                    size=-close_size if is_long else close_size,
                                    limit_price=tp_price,
                                    parent_trade=self.strategy.trade_mapping[trade_id],
                                    entry_time=self.strategy.tradebook[trade_id]['entry_time'],
                                    tag=f"TP_{trade_id}_{tp_price}"
                                )
                                self.strategy._broker.orders.insert(0, limit_order)
                                self.strategy.active_orders[trade_id]['tp'].append(limit_order)
    
class TrailingSlModel:
    def __init__(self, strategy, trailing_sl_strategy):
        self.strategy = strategy
        self.trailing_sl_strategy = trailing_sl_strategy  # User-defined trailing SL model

    def process(self, trade_id, trade_info, current_price, current_time):
        """Trail SL levels based on user-defined trailing strategy, triggered after TP1."""
        if trade_info['remaining_size'] <= 0:
            return
        entry_price = self.strategy.trade_details[trade_id]['entry_price']
        is_long = trade_info['is_long']
        booked_levels = [entry['price'] for entry in self.strategy.trade_details[trade_id]['booked']]

        # Update highest/lowest price
        if is_long:
            self.strategy.highest_price[trade_id] = max(self.strategy.highest_price.get(trade_id, entry_price), current_price)
        else:
            self.strategy.lowest_price[trade_id] = min(self.strategy.lowest_price.get(trade_id, entry_price), current_price)

        # Check if TP1 has been hit
        booked_tp = [entry for entry in self.strategy.trade_details[trade_id]['booked'] if entry['type'] == 'tp']
        if len(booked_tp) < 1:
            return

        # Delegate trailing logic to the user-defined trailing SL strategy
        new_sl_levels = self.trailing_sl_strategy.calculate_new_sl_levels(
            trade_id, trade_info, current_price, self.strategy.highest_price.get(trade_id, entry_price) if is_long else self.strategy.lowest_price.get(trade_id, entry_price)
        )
        if new_sl_levels:
            for sl_order in self.strategy.active_orders[trade_id]['sl']:
                if sl_order in self.strategy._broker.orders:
                    self.strategy._broker.orders.remove(sl_order)
            self.strategy.active_orders[trade_id]['sl'] = []
            sl_weights = trade_info['sl_weights']
            remaining_size_for_sl = trade_info['remaining_size']
            trade_info['sl_levels'] = []
            for i, (sl_price, sl_weight) in enumerate(zip(new_sl_levels, sl_weights)):
                close_size = int(sl_weight / sum(sl_weights[i:]) * remaining_size_for_sl) if sum(sl_weights[i:]) > 0 else remaining_size_for_sl
                remaining_size_for_sl -= close_size
                if close_size == 0 and remaining_size_for_sl > 0:
                    close_size = 1
                if close_size > 0:
                    stop_order = Order(
                        broker=self.strategy._broker,
                        ticker=self.strategy.data.tickers[0] if isinstance(self.strategy.data.tickers, list) else self.strategy.data.tickers,
                        size=-close_size if is_long else close_size,
                        stop_price=sl_price,
                        parent_trade=self.strategy.trade_mapping[trade_id],
                        entry_time=self.strategy.tradebook[trade_id]['entry_time'],
                        tag=f"SL_{trade_id}_{sl_price}"
                    )
                    self.strategy._broker.orders.insert(0, stop_order)
                    self.strategy.active_orders[trade_id]['sl'].append(stop_order)
                    trade_info['sl_levels'].append({str(sl_price): sl_weight})

            print(f"Trade {trade_id} (Trailing SL): Time = {current_time}, Current Price = {current_price}, "
                  f"{'Highest' if is_long else 'Lowest'} Price = {self.strategy.highest_price.get(trade_id, entry_price) if is_long else self.strategy.lowest_price.get(trade_id, entry_price)}, "
                  f"New SL Levels = {new_sl_levels}")

class BreakevenModel:
    def __init__(self, strategy):
        self.strategy = strategy

    def process(self, trade_id, trade_info, current_price, current_time):
        """Move SL to breakeven after a TP hit."""
        pass  # To be implemented by user-defined model if needed

class MultipleEntriesModel:
    def __init__(self, strategy):
        self.strategy = strategy

    def process(self, trade_id, trade_info, current_price, current_time):
        """Placeholder for multiple entries logic."""
        pass  # To be implemented by user-defined model if needed

class BaseTradeStrategy(Strategy):
    def __init__(self, broker, data, params, *args, **kwargs):
        super().__init__(broker, data, params, *args, **kwargs)
        self.tradebook = {}
        self.active_trades = {}
        self.trade_details = {}
        self.trade_counter = 0
        self.total_trades = len(self.closed_trades)
        self.initial_cash = broker._cash
        self.active_orders = {}
        self.trade_mapping = {}
        self.pending_trades = {}
        self.highest_price = {}
        self.lowest_price = {}

    def add_buy_trade(self):
        """Create a buy trade with TP/SL levels provided by the strategy."""
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        entry_time = self.data.index[-1]

        if risk_per_trade > 0:
            weighted_sl, weighted_tp = self.trade_manager.calculate_weighted_tp_sl_levels("buy")

            tp_levels = [next(iter(tp)) for tp in weighted_tp if tp]
            tp_weights = [list(tp.values())[0] for tp in weighted_tp if tp]
            sl_levels = [next(iter(sl)) for sl in weighted_sl if sl]
            sl_weights = [list(sl.values())[0] for sl in weighted_sl if sl]

            print(f"Trade {self.trade_counter} (Buy):")
            print(f"  TP Levels: {tp_levels}")
            print(f"  TP Weights: {tp_weights}")
            print(f"  SL Levels: {sl_levels}")
            print(f"  SL Weights: {sl_weights}")

            furthest_sl = min(sl_levels) if sl_levels else entry  # Fallback to entry if no SL levels
            stop_loss_perc = abs(entry - furthest_sl) / entry if furthest_sl != entry else 0.01
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / entry)

            self.buy(size=qty, tag=f"Trade_{self.trade_counter}")

            trade_id = self.trade_counter
            self.pending_trades[trade_id] = {
                'direction': 'buy',
                'entry_price': entry,
                'entry_time': entry_time,
                'tp_levels': weighted_tp,
                'sl_levels': weighted_sl,
                'quantity': qty,
                'tp_levels_list': tp_levels,
                'sl_levels_list': sl_levels,
                'tp_weights': tp_weights,
                'sl_weights': sl_weights
            }
            self.highest_price[trade_id] = entry
            self.trade_counter += 1

    def add_sell_trade(self):
        """Create a sell trade with TP/SL levels provided by the strategy."""
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        entry_time = self.data.index[-1]

        if risk_per_trade > 0:
            weighted_sl, weighted_tp = self.trade_manager.calculate_weighted_tp_sl_levels("sell")

            tp_levels = [next(iter(tp)) for tp in weighted_tp if tp]
            tp_weights = [list(tp.values())[0] for tp in weighted_tp if tp]
            sl_levels = [next(iter(sl)) for sl in weighted_sl if sl]
            sl_weights = [list(sl.values())[0] for sl in weighted_sl if sl]

            print(f"Trade {self.trade_counter} (Sell):")
            print(f"  TP Levels: {tp_levels}")
            print(f"  TP Weights: {tp_weights}")
            print(f"  SL Levels: {sl_levels}")
            print(f"  SL Weights: {sl_weights}")

            furthest_sl = max(sl_levels) if sl_levels else entry  
            stop_loss_perc = abs(furthest_sl - entry) / entry if furthest_sl != entry else 0.01
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / entry)

            self.sell(size=qty, tag=f"Trade_{self.trade_counter}")

            trade_id = self.trade_counter
            self.pending_trades[trade_id] = {
                'direction': 'sell',
                'entry_price': entry,
                'entry_time': entry_time,
                'tp_levels': weighted_tp,
                'sl_levels': weighted_sl,
                'quantity': qty,
                'tp_levels_list': tp_levels,
                'sl_levels_list': sl_levels,
                'tp_weights': tp_weights,
                'sl_weights': sl_weights
            }
            self.lowest_price[trade_id] = entry
            self.trade_counter += 1

    def on_trade_close(self):
        """Update risk management after trades close."""
        num_closed = len(self.closed_trades) - self.total_trades
        if num_closed > 0:
            for trade in self.closed_trades[-num_closed:]:
                if trade.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()
        self.total_trades = len(self.closed_trades)

    def calculate_pnl(self, entry_price, exit_price, size, is_long):
        """Calculate profit/loss for a trade exit."""
        if is_long:
            return (exit_price - entry_price) * size
        else:
            return (entry_price - exit_price) * size

    def export_tradebook(self, filename="tradebook.csv"):
        """Export trade results to CSV."""
        trade_records = []
        for trade_id, trade in self.tradebook.items():
            record = {
                'Trade_ID': trade_id,
                'Direction': trade['direction'],
                'Entry_Price': trade['entry_price'],
                'Entry_Time': trade['entry_time'],
                'Initial_Quantity': trade['quantity'],
                'TP_Levels': str(trade['tp_levels']),
                'SL_Levels': str(trade['sl_levels']),
                'Final_SL_Levels': str(self.active_trades.get(trade_id, {}).get('sl_levels', trade['sl_levels'])),
                'Initial_Cash': trade['initial_cash'],
                'Initial_Position_Value': trade['initial_position_value']
            }
            total_pnl = 0
            for i, exit in enumerate(trade['exits']):
                record[f'Exit_{i+1}_Price'] = exit['price']
                record[f'Exit_{i+1}_Size'] = exit['size']
                record[f'Exit_{i+1}_Time'] = exit['time']
                record[f'Exit_{i+1}_Type'] = exit['type']
                record[f'Exit_{i+1}_PnL'] = exit['pnl']
                record[f'Exit_{i+1}_Cash_After'] = exit['cash_after']
                record[f'Exit_{i+1}_Remaining_Qty'] = exit['remaining_qty']
                record[f'Exit_{i+1}_Position_Value'] = exit['position_value']
                total_pnl += exit['pnl']
            record['Total_PnL'] = total_pnl
            trade_records.append(record)
        df = pd.DataFrame(trade_records)
        df.to_csv(filename, index=False)
        print(f"Tradebook exported to {filename}")

    def setup_trade(self, trade_id, trade_info, trade):
        """Set up trade bookkeeping."""
        qty = trade_info['quantity']
        entry_price = trade_info['entry_price']
        entry_time = trade_info['entry_time']
        weighted_tp = trade_info['tp_levels']
        weighted_sl = trade_info['sl_levels']
        is_long = trade_info['direction'] == 'buy'

        self.tradebook[trade_id] = {
            'direction': trade_info['direction'],
            'entry_price': entry_price,
            'entry_time': entry_time,
            'tp_levels': weighted_tp,
            'sl_levels': weighted_sl,
            'quantity': qty,
            'exits': [],
            'initial_cash': self._broker._cash,
            'initial_position_value': qty * entry_price
        }
        self.active_trades[trade_id] = {
            'sl_levels': weighted_sl,
            'initial_qty': qty,
            'remaining_size': qty,
            'is_long': is_long,
            'sl_weights': trade_info['sl_weights'],
            'tp_weights': trade_info['tp_weights']  # Add tp_weights for consistency
        }
        self.trade_details[trade_id] = {
            'entry_price': entry_price,
            'sl_levels': weighted_sl,
            'tp_levels': weighted_tp,
            'booked': []
        }
        self.active_orders[trade_id] = {'tp': [], 'sl': []}
        self.trade_mapping[trade_id] = trade
        self.highest_price[trade_id] = entry_price if is_long else None
        self.lowest_price[trade_id] = entry_price if not is_long else None

        # Delegate TP/SL order setup to MultiTpSlModel if defined
        if hasattr(self, 'multi_tp_sl_model'):
            self.multi_tp_sl_model.setup_trade(trade_id, trade_info, trade)
    def next(self):
        """Process each bar in the backtest, calling model methods sequentially."""
        current_price = self.data.Close[-1]
        current_time = self.data.index[-1]
        self.on_trade_close()

        # Process pending trades
        for trade_id in list(self.pending_trades.keys()):
            trade_info = self.pending_trades[trade_id]
            trade = None
            for t in self.trades():
                if t.tag == f"Trade_{trade_id}":
                    trade = t
                    break
            if trade:
                self.setup_trade(trade_id, trade_info, trade)
                del self.pending_trades[trade_id]

        # Process active trades with defined models
        for trade_id, trade_info in list(self.active_trades.items()):
            entry_time = self.tradebook[trade_id]['entry_time']
            if current_time <= entry_time:
                continue
            if trade_info['remaining_size'] <= 0:
                for order in self.active_orders[trade_id]['tp'] + self.active_orders[trade_id]['sl']:
                    if order in self._broker.orders:  # Changed from self.strategy._broker.orders
                        self._broker.orders.remove(order)
                del self.active_trades[trade_id]
                del self.active_orders[trade_id]
                del self.trade_mapping[trade_id]
                if trade_id in self.highest_price:
                    del self.highest_price[trade_id]
                if trade_id in self.lowest_price:
                    del self.lowest_price[trade_id]
                continue

            # Call processing methods for defined models
            if hasattr(self, 'multi_tp_sl_model'):
                self.multi_tp_sl_model.process(trade_id, trade_info, current_price, current_time)
            if hasattr(self, 'trailing_sl_model'):
                self.trailing_sl_model.process(trade_id, trade_info, current_price, current_time)
            if hasattr(self, 'breakeven_model'):
                self.breakeven_model.process(trade_id, trade_info, current_price, current_time)
            if hasattr(self, 'multiple_entries_model'):
                self.multiple_entries_model.process(trade_id, trade_info, current_price, current_time)

            # Clean up if trade is fully exited
            if trade_info['remaining_size'] <= 0:
                for order in self.active_orders[trade_id]['tp'] + self.active_orders[trade_id]['sl']:
                    if order in self._broker.orders:  # Changed from self.strategy._broker.orders
                        self._broker.orders.remove(order)
                del self.active_trades[trade_id]
                del self.active_orders[trade_id]
                del self.trade_mapping[trade_id]
                if trade_id in self.highest_price:
                    del self.highest_price[trade_id]
                if trade_id in self.lowest_price:
                    del self.lowest_price[trade_id]