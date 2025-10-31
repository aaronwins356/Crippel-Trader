"""Base abstractions for strategy engines."""
from __future__ import annotations

import abc
from dataclasses import dataclass

from ..domain import MarketData, TradeAction
from ..execution.base import PortfolioState


@dataclass(slots=True)
class StrategyConfig:
    """Marker dataclass for strategy configurations."""


class BaseStrategy(abc.ABC):
    """Base class for all synchronous strategy implementations."""

    def __init__(self, config: StrategyConfig) -> None:
        self._config = config

    @abc.abstractmethod
    def on_market_data(self, market: MarketData, portfolio: PortfolioState) -> TradeAction:
        """Return a trade action given the latest market tick and portfolio."""
