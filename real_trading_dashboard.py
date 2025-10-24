#!/usr/bin/env python3
"""Enhanced Real Trading Dashboard with live market data and capital management."""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import numpy as np

# Page configuration
st.set_page_config(
    page_title="🐊 Croc-Bot Real Trading Dashboard",
    page_icon="🐊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .profit-positive {
        color: #00ff00;
        font-weight: bold;
    }
    .profit-negative {
        color: #ff4444;
        font-weight: bold;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000/api"

class RealTradingAPI:
    """API client for real trading system."""
    
    @staticmethod
    def get_status():
        """Get real trading system status."""
        try:
            response = requests.get(f"{API_BASE_URL}/real-trading/status", timeout=5)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    @staticmethod
    def get_portfolio():
        """Get real trading portfolio."""
        try:
            response = requests.get(f"{API_BASE_URL}/real-trading/portfolio", timeout=5)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    @staticmethod
    def get_risk_metrics():
        """Get risk metrics."""
        try:
            response = requests.get(f"{API_BASE_URL}/real-trading/risk-metrics", timeout=5)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    @staticmethod
    def get_market_data(symbol: str):
        """Get market data for symbol."""
        try:
            response = requests.get(f"{API_BASE_URL}/real-trading/market-data/{symbol}", timeout=5)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    @staticmethod
    def start_trading(config: dict):
        """Start real trading system."""
        try:
            response = requests.post(f"{API_BASE_URL}/real-trading/start", json=config, timeout=10)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    @staticmethod
    def stop_trading():
        """Stop real trading system."""
        try:
            response = requests.post(f"{API_BASE_URL}/real-trading/stop", timeout=10)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    @staticmethod
    def execute_manual_trade(trade_data: dict):
        """Execute manual trade."""
        try:
            response = requests.post(f"{API_BASE_URL}/real-trading/manual-trade", json=trade_data, timeout=10)
            return response.json() if response.status_code == 200 else None
        except:
            return None

def main():
    """Main dashboard application."""
    
    # Header
    st.markdown('<div class="main-header">🐊 Croc-Bot Real Trading Dashboard</div>', unsafe_allow_html=True)
    st.markdown("**Professional Trading System with Live Market Data & Capital Management**")
    
    # Initialize session state
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()
    
    # Sidebar - System Controls
    with st.sidebar:
        st.header("🎛️ System Controls")
        
        # Get current status
        status = RealTradingAPI.get_status()
        
        if status and status.get('is_running'):
            st.markdown('<div class="success-box">✅ Real Trading System ACTIVE</div>', unsafe_allow_html=True)
            
            if st.button("🛑 Stop Trading System", type="secondary"):
                result = RealTradingAPI.stop_trading()
                if result:
                    st.success("Trading system stopped!")
                    st.rerun()
                else:
                    st.error("Failed to stop trading system")
        
        else:
            st.markdown('<div class="warning-box">⚠️ Real Trading System INACTIVE</div>', unsafe_allow_html=True)
            
            st.subheader("Start Trading System")
            
            initial_capital = st.number_input("Initial Capital ($)", min_value=100.0, max_value=100000.0, value=1000.0, step=100.0)
            risk_aggression = st.slider("Risk Level", min_value=1, max_value=10, value=5, help="1=Conservative, 10=Aggressive")
            max_positions = st.number_input("Max Positions", min_value=1, max_value=20, value=5)
            
            if st.button("🚀 Start Real Trading", type="primary"):
                config = {
                    "initial_capital": initial_capital,
                    "risk_aggression": risk_aggression,
                    "max_positions": max_positions,
                    "enable_real_trading": True
                }
                
                result = RealTradingAPI.start_trading(config)
                if result:
                    st.success("Real trading system started!")
                    st.rerun()
                else:
                    st.error("Failed to start trading system")
        
        st.markdown("---")
        
        # Manual Trading
        st.subheader("📊 Manual Trading")
        
        if status and status.get('is_running'):
            symbol = st.selectbox("Symbol", ["BTC/USD", "ETH/USD", "ADA/USD", "SOL/USD", "TSLA", "AAPL", "GOOGL", "MSFT", "NVDA", "SPY"])
            side = st.selectbox("Side", ["BUY", "SELL"])
            size = st.number_input("Size", min_value=0.001, max_value=1000.0, value=0.1, step=0.001, format="%.6f")
            order_type = st.selectbox("Order Type", ["LIMIT", "MARKET"])
            
            if order_type == "LIMIT":
                price = st.number_input("Limit Price", min_value=0.01, value=100.0, step=0.01)
            else:
                price = None
            
            if st.button("Execute Trade", type="primary"):
                trade_data = {
                    "symbol": symbol,
                    "side": side,
                    "size": size,
                    "order_type": order_type,
                    "price": price
                }
                
                result = RealTradingAPI.execute_manual_trade(trade_data)
                if result:
                    st.success(f"Trade executed: {side} {size} {symbol}")
                else:
                    st.error("Trade failed - check validation")
        else:
            st.info("Start trading system to enable manual trading")
        
        # Auto-refresh
        st.markdown("---")
        auto_refresh = st.checkbox("Auto Refresh (5s)", value=True)
        if auto_refresh:
            time.sleep(5)
            st.rerun()
    
    # Main content
    if not status or not status.get('is_running'):
        st.markdown('<div class="warning-box">⚠️ Real Trading System is not running. Use the sidebar to start it.</div>', unsafe_allow_html=True)
        return
    
    # Get data
    portfolio = RealTradingAPI.get_portfolio()
    risk_metrics = RealTradingAPI.get_risk_metrics()
    
    if not portfolio:
        st.error("Failed to load portfolio data")
        return
    
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        equity = portfolio.get('equity', 0)
        st.metric("💰 Total Equity", f"${equity:,.2f}")
    
    with col2:
        cash = portfolio.get('cash', 0)
        st.metric("💵 Available Cash", f"${cash:,.2f}")
    
    with col3:
        daily_pnl = portfolio.get('daily_pnl', 0)
        daily_pnl_color = "profit-positive" if daily_pnl >= 0 else "profit-negative"
        st.metric("📈 Daily P&L", f"${daily_pnl:,.2f}", delta=f"{daily_pnl:+.2f}")
    
    with col4:
        total_pnl = portfolio.get('total_pnl', 0)
        total_pnl_pct = (total_pnl / 1000) * 100 if equity > 0 else 0
        st.metric("📊 Total P&L", f"${total_pnl:,.2f}", delta=f"{total_pnl_pct:+.1f}%")
    
    with col5:
        max_drawdown = portfolio.get('max_drawdown', 0) * 100
        st.metric("📉 Max Drawdown", f"{max_drawdown:.1f}%")
    
    # Portfolio Overview
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Portfolio Positions")
        
        positions = portfolio.get('positions', [])
        if positions:
            positions_df = pd.DataFrame(positions)
            
            # Add current values and P&L colors
            for i, pos in enumerate(positions):
                pnl = pos.get('unrealized_pnl', 0) + pos.get('realized_pnl', 0)
                positions_df.loc[i, 'total_pnl'] = pnl
                positions_df.loc[i, 'value'] = pos.get('size', 0) * pos.get('avg_price', 0)
            
            # Format for display
            display_df = positions_df[['symbol', 'size', 'avg_price', 'value', 'total_pnl']].copy()
            display_df.columns = ['Symbol', 'Size', 'Avg Price', 'Value ($)', 'P&L ($)']
            display_df['Avg Price'] = display_df['Avg Price'].apply(lambda x: f"${x:.2f}")
            display_df['Value ($)'] = display_df['Value ($)'].apply(lambda x: f"${x:.2f}")
            display_df['P&L ($)'] = display_df['P&L ($)'].apply(lambda x: f"${x:+.2f}")
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No open positions")
    
    with col2:
        st.subheader("📋 Open Orders")
        
        orders = portfolio.get('open_orders', [])
        if orders:
            orders_df = pd.DataFrame(orders)
            display_orders = orders_df[['symbol', 'side', 'size', 'price']].copy()
            display_orders.columns = ['Symbol', 'Side', 'Size', 'Price']
            display_orders['Price'] = display_orders['Price'].apply(lambda x: f"${x:.2f}")
            st.dataframe(display_orders, use_container_width=True)
        else:
            st.info("No open orders")
    
    # Risk Management Dashboard
    st.markdown("---")
    st.subheader("🛡️ Risk Management")
    
    if risk_metrics:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Position Limits**")
            current_equity = risk_metrics.get('current_equity', 0)
            max_position = risk_metrics.get('max_position_size_usd', 0)
            st.metric("Max Position Size", f"${max_position:,.0f}")
            
            total_exposure = risk_metrics.get('total_exposure', 0)
            max_exposure = risk_metrics.get('max_total_exposure_usd', 0)
            exposure_pct = (total_exposure / max_exposure * 100) if max_exposure > 0 else 0
            st.metric("Exposure Used", f"{exposure_pct:.1f}%", delta=f"${total_exposure:,.0f} / ${max_exposure:,.0f}")
        
        with col2:
            st.markdown("**Cash Management**")
            available_cash = risk_metrics.get('available_cash', 0)
            cash_reserve = risk_metrics.get('cash_reserve_usd', 0)
            st.metric("Available Cash", f"${available_cash:,.0f}")
            st.metric("Cash Reserve", f"${cash_reserve:,.0f}")
        
        with col3:
            st.markdown("**Risk Limits**")
            risk_limits = risk_metrics.get('risk_limits', {})
            st.metric("Max Daily Loss", f"{risk_limits.get('max_daily_loss_pct', 0):.1f}%")
            st.metric("Max Position", f"{risk_limits.get('max_position_size_pct', 0):.1f}%")
    
    # Live Market Data
    st.markdown("---")
    st.subheader("📈 Live Market Data")
    
    # Get market data for key symbols
    symbols = ["BTC/USD", "ETH/USD", "TSLA", "AAPL", "SPY"]
    market_data = []
    
    for symbol in symbols:
        data = RealTradingAPI.get_market_data(symbol)
        if data:
            market_data.append({
                'Symbol': symbol,
                'Price': f"${data.get('price', 0):.2f}",
                'Bid': f"${data.get('bid', 0):.2f}",
                'Ask': f"${data.get('ask', 0):.2f}",
                'Spread': f"{data.get('spread', 0):.4f}",
                'Market Open': "✅" if data.get('market_open', False) else "❌"
            })
    
    if market_data:
        market_df = pd.DataFrame(market_data)
        st.dataframe(market_df, use_container_width=True)
    
    # Trading Statistics
    st.markdown("---")
    st.subheader("📊 Trading Statistics")
    
    stats = portfolio.get('stats', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", stats.get('total_trades', 0))
    
    with col2:
        st.metric("Winning Trades", stats.get('winning_trades', 0))
    
    with col3:
        st.metric("Losing Trades", stats.get('losing_trades', 0))
    
    with col4:
        win_rate = stats.get('win_rate', 0)
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    # System Status
    st.markdown("---")
    st.subheader("🔧 System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.json({
            "System Running": status.get('is_running', False),
            "Current Equity": f"${status.get('current_equity', 0):,.2f}",
            "Available Cash": f"${status.get('available_cash', 0):,.2f}",
            "Open Positions": status.get('open_positions', 0),
            "Open Orders": status.get('open_orders', 0),
            "Trades Today": status.get('trades_today', 0)
        })
    
    with col2:
        st.json({
            "Subscribed Symbols": status.get('subscribed_symbols', []),
            "Active Strategies": status.get('strategies_active', []),
            "Last Update": status.get('last_update', 'Unknown')
        })
    
    # Footer
    st.markdown("---")
    st.markdown("**🐊 Croc-Bot Real Trading System** - Professional algorithmic trading with live market data")
    st.markdown("⚠️ **Risk Warning**: This system trades with real money. Past performance does not guarantee future results.")

if __name__ == "__main__":
    main()