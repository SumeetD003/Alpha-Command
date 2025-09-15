# Alpha-Command

A comprehensive modular framework for backtesting, strategy development, and risk management across equities, forex, commodities, and crypto markets. Built on top of Backtesting.py with extensive enhancements for multi-asset trading, advanced risk management, and live trading capabilities.

##  Key Features

### Core Framework
- **Multi-Asset Backtesting**: Support for equities, forex, commodities, and cryptocurrencies
- **Strategy Development**: Extensive library of pre-built strategies and indicators
- **Risk Management**: 25+ risk management modules including Kelly Criterion, Martingale, Fibonacci, and more
- **Trade Management**: Advanced position sizing, take-profit/stop-loss, and trailing stop systems
- **Live Trading**: Integration with multiple brokers including Interactive Brokers, MT5, and CCXT

### Data Sources
- **Multiple Data Providers**: Yahoo Finance, Alpaca, EODHD, Tiingo, Interactive Brokers, and more
- **Real-time & Historical Data**: Seamless integration for both backtesting and live trading
- **Multi-timeframe Support**: Handle multiple timeframes simultaneously

### Advanced Analytics
- **QuantStats Integration**: Comprehensive performance analytics and reporting
- **Monte Carlo Simulation**: Risk assessment through statistical modeling
- **Hyperparameter Optimization**: Automated strategy parameter tuning
- **Walk-Forward Analysis**: Robust out-of-sample testing

##  Project Structure

```
Alpha-Command/
├── TradeMaster/                 # Core framework
│   ├── backtesting.py          # Enhanced backtesting engine
│   ├── forwardtesting.py       # Forward testing capabilities
│   ├── broker_aggregator/      # Multi-broker integration
│   ├── datasource/             # Data provider integrations
│   ├── risk_management/        # 25+ risk management strategies
│   ├── trade_management/       # Position and trade management
│   ├── helpers/                # Technical indicators and utilities
│   ├── quantstats/             # Performance analytics
│   └── FrontEnd/               # Streamlit dashboard
├── strategies_folder/          # Pre-built trading strategies
├── examples/                   # Tutorials and examples
└── test/                       # Test suite
```

##  Installation

```bash
# Clone the repository
git clone https://github.com/your-username/Alpha-Command.git
cd Alpha-Command

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

##  Quick Start

### Basic Strategy Example

```python
from TradeMaster.backtesting import Strategy
from TradeMaster.helpers.indicators import calculate_atr
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement

class SmaCross(Strategy):
    n1 = 20
    n2 = 50
    
    def init(self):
        self.sma1 = self.I(self.data.df.ta.sma(self.n1))
        self.sma2 = self.I(self.data.df.ta.sma(self.n2))
        self.risk_mgmt = EqualRiskManagement(initial_risk_per_trade=0.01)
    
    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.sell()
```

### Running a Backtest

```python
from TradeMaster.backtesting import Backtest
from TradeMaster.datasource.yahoo import YahooData

# Load data
data = YahooData('AAPL', start='2020-01-01', end='2023-01-01')

# Run backtest
bt = Backtest(data, SmaCross, cash=10000, commission=0.002)
results = bt.run()

# View results
bt.plot()
print(results)
```

##  Available Strategies

### Technical Analysis Strategies
- **ADX Trend Strategy**: Average Directional Index based trend following
- **Bollinger Bands Reversal**: Mean reversion using Bollinger Bands
- **EMA Crossover RSI**: Moving average crossover with RSI confirmation
- **Golden Harmony Breakout**: Multi-timeframe breakout strategy
- **Supertrend**: Trend following with dynamic stop-loss
- **Grid Trading**: Systematic grid-based trading

### Machine Learning Strategies
- **ML Train Once**: Single training session with walk-forward validation
- **ML Walk Forward**: Continuous retraining and validation

##  Risk Management Modules

- **Kelly Criterion**: Optimal position sizing based on win probability
- **Martingale/Anti-Martingale**: Progressive betting systems
- **Fibonacci**: Fibonacci-based position sizing
- **CPPI**: Constant Proportion Portfolio Insurance
- **Volatility ATR**: ATR-based risk management
- **Portfolio Heat**: Portfolio-level risk control
- **Market Regime ADX**: Regime-aware risk management

##  Data Sources

- **Yahoo Finance**: Free historical and real-time data
- **Alpaca**: Commission-free trading and market data
- **EODHD**: End-of-day and real-time data
- **Interactive Brokers**: Professional trading platform
- **MT5**: MetaTrader 5 integration
- **CCXT**: Cryptocurrency exchange integration

##  Advanced Features

### Multi-Asset Backtesting
```python
# Backtest multiple assets simultaneously
symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
data = YahooData(symbols, start='2020-01-01', end='2023-01-01')
bt = Backtest(data, MultiAssetStrategy)
```

### Live Trading
```python
from TradeMaster.broker_aggregator import BrokerAggregator

# Initialize broker
broker = BrokerAggregator('alpaca', api_key='your_key')
strategy = SmaCross()
broker.run_live(strategy)
```

### Performance Analytics
```python
import TradeMaster.quantstats as qs

# Generate comprehensive performance report
qs.reports.html(results, output='report.html')
```

##  Documentation

- **[Backtesting Guide](examples/backtesting.md)**: Comprehensive backtesting documentation
- **[Strategy Examples](examples/)**: Jupyter notebooks with strategy implementations
- **[API Reference](TradeMaster/)**: Complete API documentation

