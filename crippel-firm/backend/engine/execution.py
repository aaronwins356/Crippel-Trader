"""Signal-to-order translation respecting long-only policy."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal, Optional

from .portfolio import Portfolio
from .params import StrategyParams


@dataclass
class Signal:
    symbol: str
    confidence: float
    price: float
    reason: str
    latency_ms: float = 0.0


@dataclass
class OrderIntent:
    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    price: float
    reason: str


class ExecutionEngine:
    """Translate analyst signals into actionable orders."""

    def __init__(self, portfolio: Portfolio, params: StrategyParams) -> None:
        self.portfolio = portfolio
        self.params = params

    def plan(self, signal: Signal) -> Optional[OrderIntent]:
        if signal.confidence <= 0:
            return None
        price = signal.price
        if price <= 0:
            return None
        equity = self.portfolio.total_equity()
        target_value = equity * min(0.95, self.params.size_frac * signal.confidence * 2)
        position = self.portfolio.position(signal.symbol)
        current_value = (position.quantity * price) if position else 0.0
        delta_value = target_value - current_value
        if abs(delta_value) < price * 0.01:
            return None
        if delta_value > 0:
            side: Literal["BUY", "SELL"] = "BUY"
            quantity = delta_value / price
        else:
            side = "SELL"
            if not position:
                return None
            quantity = min(position.quantity, abs(delta_value) / price)
            if quantity <= 1e-6:
                return None
        order_id = uuid.uuid4().hex
        return OrderIntent(order_id=order_id, symbol=signal.symbol, side=side, quantity=quantity, price=price, reason=signal.reason)
