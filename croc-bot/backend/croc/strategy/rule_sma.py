"""Simple SMA crossover strategy for baselining."""

from __future__ import annotations

from typing import Mapping, Optional

import numpy as np

from ..config import StrategyConfig
from ..models.types import Order, OrderType, Position, Side, Tick
from .base import BaseStrategy


class SMAStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config)
        params = config.params
        self.order_size: float = float(params.get("order_size", 0.01))
        self.threshold: float = float(params.get("threshold", 0.0))

    async def on_tick(self, tick: Tick, features: np.ndarray, position: Position) -> Optional[Order]:
        spread = float(features[1])  # fast - slow
        if spread > self.threshold and position.size <= 0:
            return self.new_order(
                symbol=tick.symbol,
                side=Side.BUY,
                size=self.order_size,
                price=tick.ask,
                order_type=OrderType.MARKET,
            )
        if spread < -self.threshold and position.size >= 0:
            return self.new_order(
                symbol=tick.symbol,
                side=Side.SELL,
                size=self.order_size,
                price=tick.bid,
                order_type=OrderType.MARKET,
            )
        return None

    def configure(self, params: Mapping[str, float]) -> None:
        super().configure(params)
        if "order_size" in params:
            self.order_size = float(params["order_size"])
        if "threshold" in params:
            self.threshold = float(params["threshold"])


__all__ = ["SMAStrategy"]
