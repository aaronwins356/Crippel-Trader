"""Base abstractions for risk evaluation."""
from __future__ import annotations

import abc
from dataclasses import dataclass

from ..domain import MarketData, TradeAction
from ..execution.base import PortfolioState


@dataclass(slots=True)
class RiskConfig:
    """Base dataclass for risk manager configuration."""


class BaseRiskManager(abc.ABC):
    """Evaluates trade actions against portfolio-level constraints."""

    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    @abc.abstractmethod
    def evaluate(self, action: TradeAction, market: MarketData, portfolio: PortfolioState) -> TradeAction:
        """Return the risk-adjusted trade action."""
