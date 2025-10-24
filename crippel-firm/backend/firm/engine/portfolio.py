"""Portfolio accounting utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from .kraken_adapter import Order
from .simulator import SimulatedMarketData


@dataclass
class Position:
    quantity: float = 0.0
    avg_price: float = 0.0


@dataclass
class Portfolio:
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0

    def calculate_order_size(self, price: float, conviction: float) -> float:
        budget = self.cash * conviction
        if price <= 0:
            return 0.0
        quantity = budget / price
        return round(quantity, 6)

    def apply_fill(self, order: Order) -> None:
        position = self.positions.setdefault(order.symbol, Position())
        if order.side == "buy":
            total_cost = position.avg_price * position.quantity + order.price * order.quantity
            position.quantity += order.quantity
            position.avg_price = total_cost / position.quantity if position.quantity else 0.0
            self.cash -= order.price * order.quantity
        elif order.side == "sell":
            realized = (order.price - position.avg_price) * order.quantity
            self.realized_pnl += realized
            position.quantity -= order.quantity
            if position.quantity <= 0:
                position.quantity = 0
                position.avg_price = 0
            self.cash += order.price * order.quantity
        else:
            raise ValueError("Unsupported order side")

    def unrealized_pnl(self, market_data: SimulatedMarketData) -> float:
        pnl = 0.0
        for symbol, position in self.positions.items():
            if position.quantity <= 0:
                continue
            price = market_data.current_price(symbol)
            pnl += (price - position.avg_price) * position.quantity
        return pnl

    def current_exposure(self) -> float:
        exposure = 0.0
        for symbol, position in self.positions.items():
            exposure += position.avg_price * position.quantity
        return exposure
