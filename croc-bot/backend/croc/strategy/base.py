"""Strategy interface."""

from __future__ import annotations

import abc
import itertools
from typing import Optional

import numpy as np

from ..config import StrategyConfig
from ..models.types import Fill, Order, Position, Tick


class BaseStrategy(abc.ABC):
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config
        self._order_seq = itertools.count(1)

    async def warmup(self, history: list[Tick]) -> None:
        return None

    @abc.abstractmethod
    async def on_tick(self, tick: Tick, features: np.ndarray, position: Position) -> Optional[Order]:
        """Handle a tick and optionally produce an order."""

    async def on_fill(self, fill: Fill, position: Position) -> None:
        return None

    async def teardown(self) -> None:
        return None

    def new_order(self, **kwargs) -> Order:
        order_id = f"{self.config.name}-{next(self._order_seq)}"
        return Order(id=order_id, **kwargs)


__all__ = ["BaseStrategy"]
