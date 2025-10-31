"""Baseline deterministic risk manager."""
from __future__ import annotations

from dataclasses import dataclass

from ..domain import MarketData, TradeAction, TradeSignal
from ..execution.base import PortfolioState
from .base import BaseRiskManager, RiskConfig


@dataclass(slots=True)
class SimpleRiskConfig(RiskConfig):
    """Risk parameters for the simple risk manager."""

    max_drawdown: float
    stop_loss_pct: float
    position_size_pct: float
    max_position_value: float

    def __post_init__(self) -> None:
        if not 0 < self.max_drawdown < 1:
            raise ValueError("max_drawdown must be between 0 and 1")
        if not 0 < self.stop_loss_pct < 1:
            raise ValueError("stop_loss_pct must be between 0 and 1")
        if not 0 < self.position_size_pct <= 1:
            raise ValueError("position_size_pct must be between 0 and 1")
        if self.max_position_value <= 0:
            raise ValueError("max_position_value must be positive")


class SimpleRiskManager(BaseRiskManager):
    """Risk manager enforcing deterministic limits and stop losses."""

    def __init__(self, config: SimpleRiskConfig) -> None:
        super().__init__(config)
        self._config = config

    def evaluate(self, action: TradeAction, market: MarketData, portfolio: PortfolioState) -> TradeAction:
        if portfolio.drawdown >= self._config.max_drawdown:
            return TradeAction(signal=TradeSignal.HOLD, metadata={"reason": "max_drawdown"})

        if portfolio.position_units > 0 and portfolio.avg_entry_price is not None:
            stop_price = portfolio.avg_entry_price * (1 - self._config.stop_loss_pct)
            if market.price <= stop_price:
                notional = portfolio.position_units * market.price
                return TradeAction(
                    signal=TradeSignal.SELL,
                    notional=notional,
                    metadata={"reason": "stop_loss"},
                )

        if action.signal == TradeSignal.HOLD:
            return TradeAction(signal=TradeSignal.HOLD, metadata=action.metadata)

        allowed_notional = self._determine_notional_limit(portfolio)
        if allowed_notional <= 0:
            return TradeAction(signal=TradeSignal.HOLD, metadata={"reason": "no_capital"})

        requested = action.notional if action.notional and action.notional > 0 else allowed_notional
        notional = min(requested, allowed_notional)

        if action.signal == TradeSignal.BUY:
            cash_available = max(portfolio.cash, 0.0)
            trade_size = min(notional, cash_available)
            if trade_size <= 0:
                return TradeAction(signal=TradeSignal.HOLD, metadata={"reason": "insufficient_cash"})
            return TradeAction(signal=TradeSignal.BUY, notional=trade_size, metadata=action.metadata)

        if action.signal == TradeSignal.SELL:
            if portfolio.position_units <= 0:
                return TradeAction(signal=TradeSignal.HOLD, metadata={"reason": "no_position"})
            max_exit = portfolio.position_units * market.price
            trade_size = min(notional, max_exit)
            if trade_size <= 0:
                return TradeAction(signal=TradeSignal.HOLD, metadata={"reason": "no_position"})
            return TradeAction(signal=TradeSignal.SELL, notional=trade_size, metadata=action.metadata)

        return TradeAction(signal=TradeSignal.HOLD, metadata={"reason": "unknown_signal"})

    def _determine_notional_limit(self, portfolio: PortfolioState) -> float:
        equity_limit = portfolio.equity * self._config.position_size_pct
        notional = min(equity_limit, self._config.max_position_value)
        return max(notional, 0.0)
