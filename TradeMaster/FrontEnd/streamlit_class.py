import os
import sys
import streamlit as st
import quantstats as qs
from TradeMaster.multi_backtester.multi_backtester import MultiBacktest
from strategies_folder.adx_trend_strategy import AdxTrendStrategy
from strategies_folder.bb_rev_strategy import BollingerBandsMeanReversion
from strategies_folder.EMAcrossoverrsi_strategy import SmaCross
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.risk_management.rpt import RiskPerTrade
from TradeMaster.risk_management.vps import VolatilityBasedPositionSizing
from TradeMaster.trade_management.tp_sl.atr_tm import Single_tp_sl
from TradeMaster.trade_management.tp_sl.std_dev import Single_tp_sl
from TradeMaster.trade_management.tp_sl.Don_Chian_tm import Single_tp_sl
from bokeh.models import Panel, Tabs
from bokeh.io import show
from bokeh.plotting import figure
from streamlit_bokeh_events import streamlit_bokeh_events

# Define RM and TM models
RM_MODELS = {
    "Equal Risk Management": EqualRiskManagement,
    "Risk Per Trade": RiskPerTrade,
    "Volatility Based Position Sizing": VolatilityBasedPositionSizing,
}

TM_MODELS = {
    "Single_tp_sl": Single_tp_sl,
    "Single_tp_sl": Single_tp_sl,
    "Single_tp_sl": Single_tp_sl,
}

# Define strategies
STRATEGIES = {
    "ADX Trend Strategy": AdxTrendStrategy,
    "Bollinger Bands Mean Reversion": BollingerBandsMeanReversion,
    "EMA Cross Strategy": SmaCross,
}


class StreamlitDashboard:
    def __init__(self):
        self.strategies = STRATEGIES
        self.rm_models = RM_MODELS
        self.tm_models = TM_MODELS

    def run_dashboard(self):
        st.title("Custom Backtesting Dashboard")

        # Sidebar for user inputs
        st.sidebar.title("Backtest Configuration")

        # Select asset
        assets = ["AAPL", "GOOG", "MSFT", "AMZN", "TSLA"]  
        selected_asset = st.sidebar.selectbox("Select Asset", assets)

        # Select strategy
        selected_strategy = st.sidebar.selectbox("Select Strategy", list(self.strategies.keys()))

        # Select RM model
        selected_rm_model = st.sidebar.selectbox("Select Risk Management Model", list(self.rm_models.keys()))

        # Select TM model
        selected_tm_model = st.sidebar.selectbox("Select Trade Management Model", list(self.tm_models.keys()))

        # Define strategy parameters
        st.sidebar.subheader("Strategy Parameters")
        strategy_params = {}
        strategy_class = self.strategies[selected_strategy]

        # Define strategy parameters based on selected strategy
        if selected_strategy == "ADX Trend Strategy":
            strategy_params['adx_period'] = st.sidebar.slider("ADX Period", 10, 30, 14)
            strategy_params['initial_risk_per_trade'] = st.sidebar.slider("Initial Risk Per Trade", 0.01, 0.1, 0.01)
            strategy_params['atr_multiplier'] = st.sidebar.slider("ATR Multiplier", 1, 5, 3)
            strategy_params['atr_period'] = st.sidebar.slider("ATR Period", 10, 30, 14)

        elif selected_strategy == "Bollinger Bands Mean Reversion":
            strategy_params['n'] = st.sidebar.slider("Bollinger Bands Period", 10, 30, 20)
            strategy_params['dev'] = st.sidebar.slider("Standard Deviation", 1, 3, 2)
            strategy_params['risk_reward_ratio'] = st.sidebar.slider("Risk Reward Ratio", 1.0, 3.0, 1.5)
            strategy_params['atr_multiplier'] = st.sidebar.slider("ATR Multiplier", 1, 5, 3)
            strategy_params['initial_risk_per_trade'] = st.sidebar.slider("Initial Risk Per Trade", 0.01, 0.1, 0.01)

        elif selected_strategy == "EMA Cross Strategy":
            strategy_params['sma10'] = st.sidebar.slider("SMA 10 Period", 5, 20, 10)
            strategy_params['sma60'] = st.sidebar.slider("SMA 60 Period", 30, 100, 60)
            strategy_params['risk_reward_ratio'] = st.sidebar.slider("Risk Reward Ratio", 1.0, 3.0, 1.5)
            strategy_params['std_dev_multiplier'] = st.sidebar.slider("Std Dev Multiplier", 1, 5, 2)
            strategy_params['std_dev_period'] = st.sidebar.slider("Std Dev Period", 10, 30, 16)
            strategy_params['initial_risk_per_trade'] = st.sidebar.slider("Initial Risk Per Trade", 0.01, 0.1, 0.01)

        if st.sidebar.button("Run Backtest"):
            st.write(f"### Running Backtest with:")
            st.write(f"**Asset:** {selected_asset}")
            st.write(f"**Strategy:** {selected_strategy}")
            st.write(f"**Risk Management Model:** {selected_rm_model}")
            st.write(f"**Trade Management Model:** {selected_tm_model}")

            # Get selected RM and TM classes
            rm_class = self.rm_models[selected_rm_model]
            tm_class = self.tm_models[selected_tm_model]


            class CustomStrategy(strategy_class):
                def __init__(self, data, *args, **kwargs):
                    super().__init__(data, *args, **kwargs)
                    # Override RM and TM models with user-selected ones
                    self.rm_model = rm_class(self)
                    self.tm_model = tm_class(self)
                    for key, value in strategy_params.items():
                        setattr(self, key, value)

            try:
                bt = MultiBacktest(CustomStrategy, cash=100000, commission=0.002, margin=1 / 100)
                stats = bt.backtest_stock(selected_asset, "1day", "us", "firstratedata")
                
                # Display basic stats
                st.write("### Backtest Results")
                st.dataframe(stats)

                # Plot Equity Curve
                st.write("### Equity Curve")
                if hasattr(bt, 'equity_curve'):
                    equity_curve = bt.equity_curve
                    p = figure(title="Equity Curve", x_axis_type='datetime', width=800, height=400, tools="pan,box_zoom,reset,save")
                    p.line(equity_curve.index, equity_curve['equity'], legend_label="Portfolio Value", line_width=2)
                    p.xaxis.axis_label = 'Date'
                    p.yaxis.axis_label = 'Value'
                    st.bokeh_chart(p)
                else:
                    st.warning("Equity curve data not available")

                # Generate Tearsheet
                st.write("### Performance Tearsheet")
                if hasattr(bt, 'returns'):
                    returns = bt.returns
                    qs.reports.html(returns, output='tearsheet.html', title='Strategy Tearsheet')
                    
                    with open('tearsheet.html', 'r') as f:
                        html = f.read()
                    
                    st.components.v1.html(html, width=1200, height=1000, scrolling=True)
                else:
                    st.warning("Return data not available for tearsheet generation")

            except Exception as e:
                st.error(f"Error during backtest: {str(e)}")

if __name__ == "__main__":
    dashboard = StreamlitDashboard()
    dashboard.run_dashboard()