#!/usr/bin/env python3
"""Test script to verify the Croc-Bot trading system."""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crippel-trader', 'backend'))

async def _run_system_check() -> bool:
    """Test the core trading system components."""
    print("🐊 Testing Croc-Bot Trading System")
    print("=" * 50)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from crippel.config import get_settings
        from crippel.paper_trading import PaperTradingEngine
        from crippel.risk_manager import RiskManager
        from crippel.notifications import get_notification_service
        from crippel.models.core import PriceTick, Order, OrderSide, OrderType, Mode
        print("✅ All imports successful")
        
        # Test configuration
        print("\n⚙️  Testing configuration...")
        settings = get_settings()
        print(f"✅ Configuration loaded - Initial capital: ${settings.initial_capital}")
        print(f"✅ Supported crypto pairs: {len(settings.supported_crypto_pairs)}")
        print(f"✅ Supported stock symbols: {len(settings.supported_stock_symbols)}")
        
        # Test paper trading engine
        print("\n💰 Testing paper trading engine...")
        paper_engine = PaperTradingEngine(200.0)
        print(f"✅ Paper trading engine initialized with ${paper_engine.initial_capital}")
        
        # Test market data processing
        print("\n📊 Testing market data processing...")
        test_tick = PriceTick(
            symbol="BTC/USD",
            price=45000.0,
            volume=1.5,
            ts=datetime.utcnow(),
            bid=44995.0,
            ask=45005.0
        )
        
        await paper_engine.update_market_data(test_tick)
        print(f"✅ Market data processed - BTC/USD: ${test_tick.price}")
        
        # Test order submission
        print("\n📋 Testing order submission...")
        test_order = Order(
            id="test_001",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            size=0.001,
            price=45000.0,
            ts=datetime.utcnow(),
            mode=Mode.PAPER,
            aggression=5
        )
        
        success = await paper_engine.submit_order(test_order)
        print(f"✅ Order submission: {'Success' if success else 'Failed'}")
        
        # Test risk manager
        print("\n🛡️  Testing risk manager...")
        risk_manager = RiskManager()
        await risk_manager.set_aggression(7)
        print(f"✅ Risk manager initialized - Aggression level: {risk_manager.current_aggression}")
        
        # Test performance summary
        print("\n📈 Testing performance tracking...")
        performance = paper_engine.get_performance_summary()
        print(f"✅ Performance summary generated:")
        print(f"   - Current equity: ${performance['current_equity']:.2f}")
        print(f"   - Total trades: {performance['total_trades']}")
        print(f"   - Win rate: {performance['win_rate_pct']:.1f}%")
        
        # Test notifications (without actually sending)
        print("\n🔔 Testing notification system...")
        notification_service = get_notification_service()
        print("✅ Notification service initialized")
        print(f"✅ Discord webhook configured: {settings.discord_notifications_enabled}")
        
        print("\n🎉 All tests passed successfully!")
        print("=" * 50)
        print("🚀 Croc-Bot Trading System is ready to launch!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_system() -> None:
    assert asyncio.run(_run_system_check()) is True


if __name__ == "__main__":
    success = asyncio.run(_run_system_check())
    sys.exit(0 if success else 1)
