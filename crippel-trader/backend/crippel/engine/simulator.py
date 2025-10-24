"""Paper trading simulator."""
from __future__ import annotations

import itertools
from datetime import datetime

from ..models.core import Fill, Order, PriceTick
from ..models.enums import Mode, OrderSide, OrderType
from .fills import PaperFillModel
from .portfolio import Portfolio


class PaperSimulator:
    """Drive order execution using paper fills."""

    def __init__(self, portfolio: Portfolio, fill_model: PaperFillModel) -> None:
        self.portfolio = portfolio
        self.fill_model = fill_model
        self._id_iter = (f"paper-{i}" for i in itertools.count(1))

    def submit(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        price: float,
        order_type: OrderType,
        aggression: int,
        mode: Mode,
    ) -> Order:
        return Order(
            id=next(self._id_iter),
            symbol=symbol,
            side=side,
            type=order_type,
            size=size,
            price=price,
            ts=datetime.utcnow(),
            mode=mode,
            aggression=aggression,
        )

    def execute(self, order: Order, tick: PriceTick) -> Fill:
        fill = self.fill_model.fill(order, price=tick.price)
        self.portfolio.update_fill(fill)
        self.portfolio.mark_price(tick.symbol, tick.price)
        return fill
