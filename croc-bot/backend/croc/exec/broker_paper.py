"""In-memory paper broker for deterministic simulations."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..models.types import Fill, Order, Side
from .broker_base import Broker


class PaperBroker(Broker):
    def __init__(self, *, slippage_bps: float = 1.0, fee_bps: float = 1.0, latency_ms: int = 5) -> None:
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
        self.latency = latency_ms / 1000
        self._mark_price: float | None = None

    def update_mark(self, price: float) -> None:
        self._mark_price = price

    async def submit(self, order: Order) -> Fill:
        await asyncio.sleep(self.latency)
        mark = order.price or self._mark_price
        if mark is None or mark <= 0:
            raise RuntimeError("No mark price available for paper fill")
        slip = mark * self.slippage_bps / 10_000
        fill_price = mark + slip if order.side is Side.BUY else mark - slip
        fee = fill_price * order.size * self.fee_bps / 10_000
        return Fill(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            price=fill_price,
            fee=fee,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def cancel_all(self) -> None:
        return None


__all__ = ["PaperBroker"]
