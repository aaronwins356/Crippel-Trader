"""Paper trading simulation engine for CrocBot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from .risk import AccountState
from .strategy import TradeSignal


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration for the simulation engine."""

    starting_balance: float
    trading_fee_bps: int


@dataclass(frozen=True)
class TradeRecord:
    """Represents a simulated trade execution."""

    timestamp: datetime
    signal: TradeSignal
    price: float
    units: float
    notional_value: float
    fee_paid: float


class SimulationEngine:
    """Executes mock trades and tracks portfolio metrics."""

    def __init__(self, config: SimulationConfig) -> None:
        if config.starting_balance <= 0:
            raise ValueError("starting_balance must be positive.")
        if config.trading_fee_bps < 0:
            raise ValueError("trading_fee_bps cannot be negative.")

        self._config = config
        self._cash = float(config.starting_balance)
        self._position_units = 0.0
        self._avg_entry_price: Optional[float] = None
        self._equity = float(config.starting_balance)
        self._peak_equity = float(config.starting_balance)
        self._position_value = 0.0
        self._drawdown = 0.0
        self._equity_history: List[float] = [self._equity]
        self._trade_log: List[TradeRecord] = []

    @property
    def trade_log(self) -> List[TradeRecord]:
        """Return the list of executed trades."""

        return list(self._trade_log)

    @property
    def equity_history(self) -> List[float]:
        """Return the equity progression."""

        return list(self._equity_history)

    def update_market(self, price: float) -> None:
        """Update portfolio metrics based on the latest market price."""

        self._position_value = self._position_units * price
        self._equity = self._cash + self._position_value
        self._peak_equity = max(self._peak_equity, self._equity)
        if self._peak_equity > 0:
            self._drawdown = max(0.0, (self._peak_equity - self._equity) / self._peak_equity)
        else:
            self._drawdown = 0.0
        self._equity_history.append(self._equity)

    def execute_trade(self, signal: TradeSignal, price: float, notional_value: float) -> Optional[TradeRecord]:
        """Execute a trade based on the provided signal and notional value."""

        if signal == TradeSignal.HOLD or notional_value <= 0:
            return None

        fee_rate = self._config.trading_fee_bps / 10_000
        timestamp = datetime.now(timezone.utc)

        if signal == TradeSignal.BUY:
            notional = min(notional_value, self._cash)
            if notional <= 0:
                return None
            units = notional / price if price > 0 else 0.0
            fee = notional * fee_rate
            self._cash -= notional + fee
            total_cost = (self._avg_entry_price or 0.0) * self._position_units
            total_cost += notional
            self._position_units += units
            if self._position_units > 0:
                self._avg_entry_price = total_cost / self._position_units
            self.update_market(price)
            record = TradeRecord(timestamp, signal, price, units, notional, fee)
            self._trade_log.append(record)
            return record

        if signal == TradeSignal.SELL:
            if self._position_units <= 0:
                return None
            desired_units = notional_value / price if price > 0 else 0.0
            units = min(desired_units, self._position_units)
            if units <= 0:
                return None
            notional = units * price
            fee = notional * fee_rate
            self._cash += notional - fee
            self._position_units -= units
            if self._position_units <= 1e-8:
                self._position_units = 0.0
                self._avg_entry_price = None
            self.update_market(price)
            record = TradeRecord(timestamp, signal, price, units, notional, fee)
            self._trade_log.append(record)
            return record

        return None

    def account_state(self) -> AccountState:
        """Return a snapshot suitable for risk evaluation."""

        return AccountState(
            cash=self._cash,
            equity=self._equity,
            position_units=self._position_units,
            position_value=self._position_value,
            avg_entry_price=self._avg_entry_price,
            peak_equity=self._peak_equity,
            drawdown=self._drawdown,
        )


__all__ = ["SimulationConfig", "TradeRecord", "SimulationEngine"]
