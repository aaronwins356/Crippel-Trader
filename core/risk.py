"""Risk management for CrocBot."""
from __future__ import annotations

from dataclasses import dataclass

from .strategy import TradeSignal


@dataclass(frozen=True)
class RiskConfig:
    """Configuration for the risk management module."""

    max_drawdown: float
    stop_loss_pct: float
    position_size_pct: float
    max_position_value: float


@dataclass(frozen=True)
class AccountState:
    """Snapshot of the current portfolio state."""

    cash: float
    equity: float
    position_units: float
    position_value: float
    avg_entry_price: float | None
    peak_equity: float
    drawdown: float


@dataclass(frozen=True)
class RiskDecision:
    """Outcome of a risk evaluation."""

    signal: TradeSignal
    notional_value: float


class RiskManager:
    """Evaluates trade signals against risk constraints."""

    def __init__(self, config: RiskConfig) -> None:
        self._config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if not 0 < self._config.max_drawdown < 1:
            raise ValueError("max_drawdown must be in the range (0, 1).")
        if not 0 < self._config.stop_loss_pct < 1:
            raise ValueError("stop_loss_pct must be in the range (0, 1).")
        if not 0 < self._config.position_size_pct <= 1:
            raise ValueError("position_size_pct must be in the range (0, 1].")
        if self._config.max_position_value <= 0:
            raise ValueError("max_position_value must be positive.")

    def assess(self, signal: TradeSignal, price: float, account: AccountState) -> RiskDecision:
        """Return a risk-adjusted trade decision."""

        if account.drawdown >= self._config.max_drawdown:
            return RiskDecision(signal=TradeSignal.HOLD, notional_value=0.0)

        if account.position_units > 0 and account.avg_entry_price is not None:
            stop_price = account.avg_entry_price * (1 - self._config.stop_loss_pct)
            if price <= stop_price:
                notional = account.position_units * price
                return RiskDecision(signal=TradeSignal.SELL, notional_value=notional)

        notional = self._determine_notional(account)

        if signal == TradeSignal.BUY:
            capital = min(account.cash, notional)
            if capital <= 0:
                return RiskDecision(signal=TradeSignal.HOLD, notional_value=0.0)
            return RiskDecision(signal=TradeSignal.BUY, notional_value=capital)

        if signal == TradeSignal.SELL:
            if account.position_units <= 0:
                return RiskDecision(signal=TradeSignal.HOLD, notional_value=0.0)
            position_value = account.position_units * price
            exit_value = max(position_value, 0.0)
            return RiskDecision(signal=TradeSignal.SELL, notional_value=exit_value)

        return RiskDecision(signal=TradeSignal.HOLD, notional_value=0.0)

    def _determine_notional(self, account: AccountState) -> float:
        """Calculate the maximum notional position allowed under risk limits."""

        equity_limit = account.equity * self._config.position_size_pct
        notional = min(equity_limit, self._config.max_position_value)
        return max(notional, 0.0)


__all__ = [
    "RiskConfig",
    "AccountState",
    "RiskDecision",
    "RiskManager",
]
