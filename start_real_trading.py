#!/usr/bin/env python3
"""Enhanced startup script for Real Croc-Bot Trading System."""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend to Python path
backend_path = Path(__file__).parent / "crippel-trader" / "backend"
sys.path.insert(0, str(backend_path))

from crippel.enhanced_trading_system import EnhancedTradingSystem, TradingSystemConfig
from crippel.config import get_settings
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def main():
    """Start the enhanced real trading system."""
    print("🐊 CROC-BOT REAL TRADING SYSTEM")
    print("=" * 50)
    print("⚠️  WARNING: This system trades with REAL money!")
    print("💰 Live market data and actual capital management")
    print("🛡️  Built-in risk management and position limits")
    print("=" * 50)
    
    # Configuration
    config = TradingSystemConfig(
        initial_capital=1000.0,  # Starting with $1000
        max_positions=5,
        enable_real_trading=True,
        risk_aggression=5,  # Medium risk (1-10 scale)
        strategy_allocation={
            "rsi": 0.25,           # 25% - RSI mean reversion
            "macd": 0.25,          # 25% - MACD trend following  
            "bollinger": 0.20,     # 20% - Bollinger Bands
            "momentum": 0.15,      # 15% - Momentum trading
            "ma_crossover": 0.10,  # 10% - Moving average crossover
            "arbitrage": 0.05,     # 5% - Arbitrage opportunities
        }
    )
    
    # Trading symbols - mix of crypto and stocks
    symbols = [
        # Major cryptocurrencies
        "BTC/USD",
        "ETH/USD", 
        "ADA/USD",
        "SOL/USD",
        
        # Major stocks (if market is open)
        "TSLA",
        "AAPL",
        "GOOGL",
        "MSFT",
        "NVDA",
        "SPY"  # S&P 500 ETF
    ]
    
    print(f"💵 Initial Capital: ${config.initial_capital:,.2f}")
    print(f"📊 Trading Symbols: {', '.join(symbols)}")
    print(f"🎯 Risk Level: {config.risk_aggression}/10")
    print(f"🔧 Active Strategies: {len(config.strategy_allocation)}")
    print()
    
    # Risk warnings
    print("🛡️  RISK MANAGEMENT FEATURES:")
    print("   • Maximum 20% capital per position")
    print("   • Maximum 80% total capital deployed")
    print("   • 10% cash reserve maintained")
    print("   • 5% daily loss limit")
    print("   • 15% maximum drawdown limit")
    print("   • Real bid/ask spreads and slippage")
    print("   • Actual trading fees applied")
    print("   • Market hours enforcement")
    print()
    
    # Confirm start
    try:
        response = input("🚀 Start real trading system? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Trading system startup cancelled")
            return
    except KeyboardInterrupt:
        print("\n❌ Startup cancelled")
        return
    
    print("\n🚀 Initializing Real Trading System...")
    
    # Initialize trading system
    trading_system = EnhancedTradingSystem(config)
    
    try:
        print("📡 Connecting to live market data...")
        print("🔍 Validating symbols and market hours...")
        print("💼 Initializing portfolio and risk management...")
        print("🤖 Starting trading strategies...")
        print()
        
        # Start the trading system
        await trading_system.start(symbols)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
        await trading_system.stop()
        print("✅ Trading system stopped safely")
        
    except Exception as e:
        logger.error("Trading system error", error=str(e))
        print(f"❌ Error: {str(e)}")
        await trading_system.stop()
        return 1
    
    return 0


def run_system():
    """Run the trading system with proper error handling."""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 System interrupted")
        return 0
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    print("🐊 Croc-Bot Real Trading System")
    print("Built with live market data and professional risk management")
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    # Run the system
    exit_code = run_system()
    sys.exit(exit_code)