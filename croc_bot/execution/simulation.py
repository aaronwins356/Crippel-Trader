"""Paper trading execution backend."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from ..domain import MarketData, TradeAction, TradeSignal
from .base import ExecutionClient, ExecutionResult, OrderStatus, PortfolioState


@dataclass(slots=True)
class SimulationConfig:
    """Configuration for the paper trading execution backend."""

    starting_balance: float
    trading_fee_bps: int

    def __post_init__(self) -> None:
        if self.starting_balance <= 0:
            raise ValueError("starting_balance must be positive")
        if self.trading_fee_bps < 0:
            raise ValueError("trading_fee_bps must be non-negative")


class SimulationExecutionClient(ExecutionClient):
    """In-memory execution venue mimicking fills and portfolio accounting."""

    def __init__(self, config: SimulationConfig) -> None:
        self._config = config
        self._cash = float(config.starting_balance)
        self._position_units = 0.0
        self._avg_entry_price: float | None = None
        self._equity = float(config.starting_balance)
        self._peak_equity = float(config.starting_balance)
        self._position_value = 0.0
        self._drawdown = 0.0
        self._last_timestamp = datetime.now(timezone.utc)
        self._trade_log: list[ExecutionResult] = []
        self._lock = asyncio.Lock()

    @property
    def trade_log(self) -> list[ExecutionResult]:
        return list(self._trade_log)

    def _fee_rate(self) -> float:
        return self._config.trading_fee_bps / 10_000

    def update_market(self, market: MarketData) -> PortfolioState:
        self._last_timestamp = market.timestamp
        self._position_value = self._position_units * market.price
        self._equity = self._cash + self._position_value
        self._peak_equity = max(self._peak_equity, self._equity)
        if self._peak_equity > 0:
            self._drawdown = max(0.0, (self._peak_equity - self._equity) / self._peak_equity)
        state = PortfolioState(
            cash=self._cash,
            equity=self._equity,
            position_units=self._position_units,
            position_value=self._position_value,
            avg_entry_price=self._avg_entry_price,
            peak_equity=self._peak_equity,
            drawdown=self._drawdown,
            timestamp=market.timestamp,
        )
        return state

    async def execute(self, action: TradeAction, market: MarketData) -> ExecutionResult:
        async with self._lock:
            return self._execute_locked(action, market)

    def _execute_locked(self, action: TradeAction, market: MarketData) -> ExecutionResult:
        state = self.update_market(market)
        if action.signal == TradeSignal.HOLD or (action.notional or 0) <= 0:
            result = ExecutionResult(
                action=action,
                status=OrderStatus.SKIPPED,
                filled_units=0.0,
                notional_value=0.0,
                fee_paid=0.0,
                portfolio=state,
            )
            return result

        fee_rate = self._fee_rate()
        executed_notional = 0.0

        if action.signal == TradeSignal.BUY:
            notional = min(action.notional or 0.0, self._cash)
            if notional <= 0:
                status = OrderStatus.REJECTED
                filled_units = 0.0
                fee_paid = 0.0
            else:
                units = notional / market.price
                fee_paid = notional * fee_rate
                self._cash -= notional + fee_paid
                total_cost = (self._avg_entry_price or 0.0) * self._position_units + notional
                self._position_units += units
                if self._position_units > 0:
                    self._avg_entry_price = total_cost / self._position_units
                filled_units = units
                status = OrderStatus.ACCEPTED
                executed_notional = notional
        elif action.signal == TradeSignal.SELL:
            if self._position_units <= 0:
                status = OrderStatus.REJECTED
                filled_units = 0.0
                fee_paid = 0.0
                notional = 0.0
            else:
                desired_units = (action.notional or 0.0) / market.price if market.price > 0 else 0.0
                units = min(desired_units or self._position_units, self._position_units)
                if units <= 0:
                    status = OrderStatus.REJECTED
                    filled_units = 0.0
                    fee_paid = 0.0
                    notional = 0.0
                else:
                    notional = units * market.price
                    fee_paid = notional * fee_rate
                    self._cash += notional - fee_paid
                    self._position_units -= units
                    if self._position_units <= 1e-9:
                        self._position_units = 0.0
                        self._avg_entry_price = None
                    filled_units = units
                    status = OrderStatus.ACCEPTED
                    executed_notional = notional
        else:
            status = OrderStatus.SKIPPED
            filled_units = 0.0
            fee_paid = 0.0
            executed_notional = 0.0

        updated_state = self.update_market(market)
        result = ExecutionResult(
            action=action,
            status=status,
            filled_units=filled_units,
            notional_value=executed_notional,
            fee_paid=fee_paid,
            portfolio=updated_state,
        )
        if status == OrderStatus.ACCEPTED:
            self._trade_log.append(result)
        return result
