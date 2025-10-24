"""Portfolio tracking and valuation."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ..models.core import Fill, PortfolioState, Position
from ..models.enums import Mode, OrderSide


class Portfolio:
    """Track cash, positions and PnL."""

    def __init__(self, starting_cash: float, mode: Mode) -> None:
        self.cash = starting_cash
        self.mode = mode
        self.positions: dict[str, Position] = defaultdict(lambda: Position(symbol=""))
        self.unrealized: dict[str, float] = defaultdict(float)

    def update_fill(self, fill: Fill) -> None:
        position = self.positions[fill.symbol]
        if not position.symbol:
            position.symbol = fill.symbol
        cost = fill.price * fill.size
        if fill.side == OrderSide.BUY:
            self.cash -= cost + fill.fee
        else:
            self.cash += cost - fill.fee
        position.update_with_fill(fill)

    def mark_price(self, symbol: str, price: float) -> None:
        position = self.positions.get(symbol)
        if position and position.size != 0:
            direction = 1.0 if position.size > 0 else -1.0
            self.unrealized[symbol] = (price - position.average_price) * abs(position.size) * direction
        else:
            self.unrealized[symbol] = 0.0

    def snapshot(self, ts: datetime) -> PortfolioState:
        total_unrealized = sum(self.unrealized.values())
        realized = sum(pos.realized_pnl for pos in self.positions.values())
        equity = self.cash + total_unrealized + realized
        return PortfolioState(
            cash=self.cash,
            equity=equity,
            pnl_realized=realized,
            pnl_unrealized=total_unrealized,
            positions={symbol: pos for symbol, pos in self.positions.items() if pos.symbol},
            mode=self.mode,
            ts=ts,
        )

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode
