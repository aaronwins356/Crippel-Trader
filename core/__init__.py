"""Core modules for CrocBot."""
from .bot import run_bot
from .feed import FeedConfig, PriceFeed
from .risk import AccountState, RiskConfig, RiskManager
from .simulation import SimulationConfig, SimulationEngine
from .strategy import MovingAverageCrossoverStrategy, StrategyConfig, TradeSignal

__all__ = [
    "run_bot",
    "FeedConfig",
    "PriceFeed",
    "AccountState",
    "RiskConfig",
    "RiskManager",
    "SimulationConfig",
    "SimulationEngine",
    "MovingAverageCrossoverStrategy",
    "StrategyConfig",
    "TradeSignal",
]
