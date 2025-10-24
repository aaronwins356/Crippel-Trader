"""Fill models for paper trading."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from ..models.core import Fill, Order


class PaperFillModel:
    """Simplistic fill simulator that assumes immediate execution."""

    def __init__(self, maker_fee_bps: float, taker_fee_bps: float) -> None:
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps

    def fill(self, order: Order, price: float) -> Fill:
        maker = order.type.name.lower() == "limit"
        fee_rate = self.maker_fee_bps if maker else self.taker_fee_bps
        fee = order.size * price * fee_rate / 10000
        return Fill(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            price=price,
            fee=fee,
            ts=datetime.utcnow(),
            maker=maker,
        )


class FillHistory:
    """Store recent fills for analytics."""

    def __init__(self, maxlen: int = 512) -> None:
        self._fills: list[Fill] = []
        self._maxlen = maxlen

    def record(self, fill: Fill) -> None:
        self._fills.append(fill)
        if len(self._fills) > self._maxlen:
            self._fills.pop(0)

    def recent(self) -> Iterable[Fill]:
        return list(self._fills)
