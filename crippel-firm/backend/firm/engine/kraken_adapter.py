"""Kraken exchange adapter (paper trading stub)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict

from ..utils.logging import get_logger


@dataclass
class Order:
    symbol: str
    side: str
    quantity: float
    price: float
    status: str = "filled"


class KrakenAdapter:
    """Simplified long-only adapter simulating Kraken interactions."""

    def __init__(self) -> None:
        self.logger = get_logger("engine.kraken")
        self._lock = asyncio.Lock()

    async def buy(self, symbol: str, quantity: float, price: float) -> Order:
        """Submit a simulated buy order."""
        if quantity <= 0:
            raise ValueError("quantity must be positive for buy orders")
        async with self._lock:
            order = Order(symbol=symbol, side="buy", quantity=quantity, price=price)
            self.logger.debug("Executed buy %s", order)
            return order

    async def sell(self, symbol: str, quantity: float, price: float) -> Order:
        """Submit a sell order used only for closing positions."""
        if quantity <= 0:
            raise ValueError("quantity must be positive for sell orders")
        async with self._lock:
            order = Order(symbol=symbol, side="sell", quantity=quantity, price=price)
            self.logger.debug("Executed sell %s", order)
            return order
