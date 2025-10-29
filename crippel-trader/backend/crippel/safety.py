"""Startup safety checks and banners for live trading mode."""
from __future__ import annotations

import asyncio
import sys
from typing import Optional

import structlog

from .config import AppSettings

logger = structlog.get_logger(__name__)


LIVE_TRADING_BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                                 ║
║   ⚠️  LIVE TRADING MODE ENABLED ⚠️                            ║
║                                                                 ║
║   Real money will be traded on Kraken exchange!                ║
║   This is NOT a simulation!                                    ║
║                                                                 ║
║   Starting in 10 seconds...                                    ║
║   Press Ctrl+C to cancel                                       ║
║                                                                 ║
╚═══════════════════════════════════════════════════════════════╝
"""

PAPER_TRADING_BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                                 ║
║   📊 PAPER TRADING MODE                                       ║
║                                                                 ║
║   Using real market data with simulated trading                ║
║   No real money will be traded                                 ║
║   Safe for testing and development                             ║
║                                                                 ║
╚═══════════════════════════════════════════════════════════════╝
"""


async def check_live_trading_safety(settings: AppSettings) -> bool:
    """Check if live trading is safely configured and get user confirmation.
    
    Args:
        settings: Application settings
    
    Returns:
        True if safe to proceed, False to abort
    """
    # Check if live trading is requested
    if not settings.is_live_trading:
        # Paper trading mode - safe to proceed
        print(PAPER_TRADING_BANNER)
        logger.info(
            "Starting in PAPER TRADING mode",
            trading_mode=settings.trading_mode,
            real_trading_flag=settings.real_trading
        )
        return True
    
    # Live trading requested - perform safety checks
    logger.warning(
        "Live trading mode requested",
        trading_mode=settings.trading_mode,
        real_trading_flag=settings.real_trading
    )
    
    # Validate API credentials
    if not settings.kraken_api_key or not settings.kraken_api_secret:
        logger.error(
            "LIVE TRADING ABORTED: Missing Kraken API credentials",
            has_api_key=bool(settings.kraken_api_key),
            has_api_secret=bool(settings.kraken_api_secret)
        )
        print("\n❌ ERROR: Kraken API credentials not configured!")
        print("   Set CRIPPEL_KRAKEN_API_KEY and CRIPPEL_KRAKEN_API_SECRET")
        print("   Or run in paper trading mode (default)\n")
        return False
    
    # Display warning banner
    print(LIVE_TRADING_BANNER)
    
    logger.critical(
        "LIVE TRADING MODE ENABLED - Real money at risk!",
        initial_capital=settings.initial_capital,
        max_capital=settings.max_capital,
        has_credentials=True
    )
    
    # 10-second countdown
    try:
        for i in range(10, 0, -1):
            print(f"   Starting live trading in {i} seconds... (Ctrl+C to cancel)", end="\r")
            sys.stdout.flush()
            await asyncio.sleep(1)
        
        print("\n")
        logger.critical("LIVE TRADING MODE ACTIVATED - Trading with real money!")
        print("✅ LIVE TRADING MODE ACTIVATED\n")
        return True
        
    except KeyboardInterrupt:
        print("\n\n❌ Live trading cancelled by user\n")
        logger.info("Live trading cancelled by user during countdown")
        return False


def print_startup_info(settings: AppSettings, version: str = "1.0.0") -> None:
    """Print startup information banner.
    
    Args:
        settings: Application settings
        version: Application version
    """
    mode_indicator = "🔴 LIVE" if settings.is_live_trading else "📊 PAPER"
    
    print(f"""
═══════════════════════════════════════════════════════════════
  Croc-Bot Trading System v{version}
  Mode: {mode_indicator}
  Environment: {settings.env.upper()}
═══════════════════════════════════════════════════════════════
    """)
    
    # Log configuration summary
    logger.info(
        "System startup",
        version=version,
        mode=mode_indicator,
        env=settings.env,
        initial_capital=settings.initial_capital,
        max_capital=settings.max_capital,
        default_aggression=settings.default_aggression,
        discord_enabled=settings.discord_notifications_enabled,
        ai_enabled=settings.ai_strategy_generation_enabled
    )


def validate_environment(settings: AppSettings) -> list[str]:
    """Validate environment configuration and return list of warnings.
    
    Args:
        settings: Application settings
    
    Returns:
        List of warning messages (empty if all OK)
    """
    warnings = []
    
    # Check market hours enforcement for live trading
    if settings.is_live_trading:
        if settings.initial_capital > settings.max_capital:
            warnings.append("Initial capital exceeds max capital - check configuration")
        
        if settings.default_aggression > 5:
            warnings.append(f"High default aggression level ({settings.default_aggression}/10) for live trading")
    
    # Check Discord configuration
    if settings.discord_notifications_enabled and not settings.discord_webhook_url:
        warnings.append("Discord notifications enabled but webhook URL not configured")
    
    # Check AI configuration
    if settings.ai_strategy_generation_enabled and not settings.openai_api_key:
        warnings.append("AI strategy generation enabled but OpenAI API key not configured")
    
    # Log warnings
    for warning in warnings:
        logger.warning("Configuration warning", message=warning)
    
    return warnings
