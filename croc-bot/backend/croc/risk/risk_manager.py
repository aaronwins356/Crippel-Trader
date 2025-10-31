"""Risk management for pre-trade checks and kill-switch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from ..config import RiskLimits
from ..models.types import Fill, Order, Position, Side


class RiskError(RuntimeError):
    """Raised when risk checks fail."""


@dataclass
class RiskState:
    equity_peak: float = 0.0
    equity_current: float = 0.0
    max_drawdown: float = 0.0
    kill_switch: bool = False


@dataclass
class RiskManager:
    limits: RiskLimits
    positions: Dict[str, Position] = field(default_factory=dict)
    state: RiskState = field(default_factory=RiskState)

    def check_order(self, order: Order, price: float) -> None:
        if self.state.kill_switch:
            raise RiskError("Kill switch active")
        projected = self._project_position(order, price)
        if abs(projected.size) > self.limits.max_position:
            raise RiskError("Position limit breached")
        notional = abs(projected.size * price)
        if notional > self.limits.max_notional:
            raise RiskError("Notional limit breached")
        if self.state.max_drawdown >= self.limits.max_daily_drawdown:
            self.state.kill_switch = True
            raise RiskError("Daily drawdown limit breached")

    def _project_position(self, order: Order, price: float) -> Position:
        position = self.positions.get(order.symbol, Position(symbol=order.symbol))
        signed = order.size if order.side is Side.BUY else -order.size
        projected = position.model_copy(update={})
        projected.size = position.size + signed
        if projected.size != 0 and position.size * projected.size >= 0:
            order_price = order.price or price
            total_notional = abs(position.avg_price) * abs(position.size) + order_price * abs(signed)
            projected.avg_price = total_notional / abs(projected.size)
        return projected

    def update_fill(self, fill: Fill) -> Position:
        position = self.positions.get(fill.symbol, Position(symbol=fill.symbol))
        position.update(fill)
        self.positions[fill.symbol] = position
        self._update_equity(position.realised_pnl)
        return position

    def _update_equity(self, realised_pnl: float) -> None:
        self.state.equity_current = realised_pnl
        self.state.equity_peak = max(self.state.equity_peak, realised_pnl)
        drawdown = self.state.equity_peak - self.state.equity_current
        self.state.max_drawdown = max(self.state.max_drawdown, drawdown)
        if self.state.max_drawdown >= self.limits.max_daily_drawdown:
            self.state.kill_switch = True

    def reset_day(self) -> None:
        self.state = RiskState()
        for position in self.positions.values():
            position.realised_pnl = 0.0

    def activate_kill_switch(self) -> None:
        self.state.kill_switch = True

    def deactivate_kill_switch(self) -> None:
        self.state.kill_switch = False
        self.state.max_drawdown = 0.0
        self.state.equity_peak = self.state.equity_current


__all__ = ["RiskManager", "RiskError", "RiskState"]
