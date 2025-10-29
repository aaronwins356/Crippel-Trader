"""Application configuration powered by pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Global application settings."""

    # Environment and core settings
    env: Literal["dev", "prod", "test"] = Field(default="dev")
    database_url: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/crippel_trading")
    
    # Trading mode and safety flags
    trading_mode: Literal["paper", "real"] = Field(default="paper")
    real_trading: int = Field(default=0, ge=0, le=1)  # 0=paper, 1=real (extra safety flag)
    
    # API credentials
    kraken_api_key: str = Field(default="")
    kraken_api_secret: str = Field(default="")
    
    @property
    def is_live_trading(self) -> bool:
        """Check if live trading is enabled (requires both flags)."""
        return self.trading_mode == "real" and self.real_trading == 1 and bool(self.kraken_api_key and self.kraken_api_secret)
    
    # Risk management and aggression
    default_aggression: int = Field(default=3, ge=1, le=10)
    initial_capital: float = Field(default=200.0, ge=0.0)
    max_capital: float = Field(default=5000.0, ge=0.0)
    
    # Trading fees and limits
    maker_fee_bps: float = Field(default=2.0, ge=0.0)
    taker_fee_bps: float = Field(default=4.0, ge=0.0)
    tick_interval_ms: int = Field(default=200, ge=10)
    history_window: int = Field(default=256, ge=32)
    
    # Risk management parameters (dynamic based on aggression)
    base_drawdown_limit: float = Field(default=0.05, ge=0.0, le=1.0)  # 5% at aggression 1
    base_per_trade_cap: float = Field(default=0.01, ge=0.0, le=1.0)   # 1% at aggression 1
    base_per_symbol_exposure: float = Field(default=0.1, ge=0.0, le=1.0)  # 10% at aggression 1
    
    # Discord notifications
    discord_webhook_url: str = Field(default="https://discord.com/api/webhooks/1431333859772862494/HRBOAWCZNWl_nzxJLJ8Kxec9fGTGErUb_ZTQxvoKEvKyUw_v3UZJdxuSUwMac0ENUDGa")
    discord_notifications_enabled: bool = Field(default=True)
    
    # AI and strategy generation
    openai_api_key: str = Field(default="")
    ai_strategy_generation_enabled: bool = Field(default=True)
    strategy_evaluation_period_hours: int = Field(default=24, ge=1)
    
    # Market data and assets
    supported_crypto_pairs: list[str] = Field(default=[
        "BTC/USD", "ETH/USD", "ADA/USD", "SOL/USD", "MATIC/USD", 
        "DOT/USD", "LINK/USD", "UNI/USD", "AAVE/USD", "ATOM/USD"
    ])
    supported_stock_symbols: list[str] = Field(default=[
        "TSLA", "AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "META", 
        "SPY", "QQQ", "IWM", "GLD", "TLT"
    ])
    
    # Backtesting and performance
    backtest_start_date: str = Field(default="2023-01-01")
    performance_benchmark: str = Field(default="SPY")
    
    # WebSocket and real-time data
    kraken_ws_url: str = Field(default="wss://ws.kraken.com")
    max_websocket_connections: int = Field(default=10, ge=1)
    
    # Dashboard and API
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:12000", "http://localhost:12001"])
    api_rate_limit: int = Field(default=100, ge=1)  # requests per minute

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CRIPPEL_", case_sensitive=False)

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]
    
    def get_dynamic_drawdown_limit(self, aggression: int) -> float:
        """Calculate drawdown limit based on aggression level (1-10)."""
        # Scale from 5% (aggression 1) to 50% (aggression 10)
        return self.base_drawdown_limit * (1 + (aggression - 1) * 1.0)
    
    def get_dynamic_per_trade_cap(self, aggression: int) -> float:
        """Calculate per-trade capital cap based on aggression level (1-10)."""
        # Scale from 1% (aggression 1) to 20% (aggression 10)
        return self.base_per_trade_cap * (1 + (aggression - 1) * 2.1)
    
    def get_dynamic_per_symbol_exposure(self, aggression: int) -> float:
        """Calculate per-symbol exposure based on aggression level (1-10)."""
        # Scale from 10% (aggression 1) to 100% (aggression 10)
        return min(1.0, self.base_per_symbol_exposure * (1 + (aggression - 1) * 1.0))
    
    def get_position_size_multiplier(self, aggression: int) -> float:
        """Get position size multiplier based on aggression level."""
        # Scale from 0.5x (conservative) to 3.0x (aggressive)
        return 0.5 + (aggression - 1) * 0.28


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()
