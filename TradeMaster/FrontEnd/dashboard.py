import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph

# Sidebar for global settings
st.sidebar.title("Settings")
ticker = st.sidebar.text_input("Ticker", "AAPL")
date_range = st.sidebar.date_input("Date Range", [])

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Home", "Backtest", "Report & AI", "Metrics", "Stock Details", "Report"])

# Tab 1: Home
with tab1:
    st.title("Welcome to the Strategy Dashboard")
    st.write("This tool allows you to backtest strategies, analyze risks, and get AI insights.")
    strategy_file = st.file_uploader("Upload your strategy file", type=["py", "csv"])

# Tab 2: Backtest
with tab2:
    st.header("Backtest Your Strategy")
    risk_model = st.selectbox("Risk Model", ["VaR", "CVaR", "Sharpe"])
    trade_model = st.selectbox("Trade Model", ["Momentum", "Mean Reversion"])
    lookback = st.slider("Lookback Period", 5, 100, 20)
    
    # Dummy equity curve
    data = pd.DataFrame({"Date": pd.date_range("2023-01-01", periods=100), "Equity": range(100)})
    fig = px.line(data, x="Date", y="Equity", title="Equity Curve")
    st.plotly_chart(fig)

# Tab 3: Report & AI
with tab3:
    st.header("Backtest Report & AI Insights")
    st.write("Metrics: Return: 12%, Drawdown: 5%")
    question = st.text_input("Ask the AI Agent")
    if question:
        st.write(f"AI Response: Analyzing '{question}'... (e.g., Increase stop-loss to 2% for better risk control)")

# Tab 4: Metrics
with tab4:
    st.header("Trade Metrics")
    pie_data = pd.DataFrame({"Category": ["Wins", "Losses"], "Value": [60, 40]})
    fig_pie = px.pie(pie_data, names="Category", values="Value", title="Win/Loss Ratio")
    st.plotly_chart(fig_pie)

# Tab 5: Stock Details
with tab5:
    st.header(f"{ticker} Details")
    stock = yf.Ticker(ticker)
    info = stock.info
    st.write(f"Market Cap: {info.get('marketCap')}, ROE: {info.get('returnOnEquity')}")

# Tab 6: Comprehensive Report
with tab6:
    st.header("Generate Report")
    if st.button("Generate PDF"):
        pdf = SimpleDocTemplate("strategy_report.pdf", pagesize=letter)
        pdf.build([Paragraph("Strategy Report: Return: 12%, Drawdown: 5%")])
        st.success("Report generated as 'strategy_report.pdf'")
