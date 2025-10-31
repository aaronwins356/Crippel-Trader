"""Strategy engines for Croc-Bot."""
from .base import BaseStrategy, StrategyConfig
from .moving_average import MovingAverageConfig, MovingAverageStrategy
from .ml import MLStrategyConfig, MLStrategy

__all__ = [
    "BaseStrategy",
    "StrategyConfig",
    "MovingAverageConfig",
    "MovingAverageStrategy",
    "MLStrategyConfig",
    "MLStrategy",
]
