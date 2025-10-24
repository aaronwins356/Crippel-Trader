"""Analyst bot aggregates research into signals."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from ..data.indicators import moving_average, relative_strength_index
from ..engine.simulator import SimulatedMarketData
from ..utils.metrics import PerformanceLedger
from .base import WorkerBot


@dataclass
class AnalystConfig:
    symbol: str = "BTC/USD"
    lookback: int = 20


class AnalystBot(WorkerBot):
    """Aggregates research events into actionable signals."""

    def __init__(
        self,
        event_bus,
        performance_ledger: PerformanceLedger,
        market_data: SimulatedMarketData,
        config: Optional[AnalystConfig] = None,
    ) -> None:
        super().__init__(event_bus=event_bus, performance_ledger=performance_ledger, bot_type="analyst")
        self.config = config or AnalystConfig()
        self.market_data = market_data
        self._research_queue: Optional[asyncio.Queue[dict[str, list[dict[str, float]]]]] = None

    async def on_start(self) -> None:
        self._research_queue = await self.subscribe("research")
        self.logger.info("AnalystBot %s started", self.bot_id)

    async def on_tick(self) -> None:
        assert self._research_queue is not None
        try:
            research = self._research_queue.get_nowait()
        except asyncio.QueueEmpty:
            research = None
        if not research:
            return
        ideas = research.get("ideas", [])
        price_history = self.market_data.price_history(self.config.symbol, self.config.lookback)
        rsi = relative_strength_index(price_history)
        ma = moving_average(price_history)
        if not price_history:
            return
        current_price = price_history[-1]
        strength = 0.0
        if ideas:
            strength += sum(idea["confidence"] for idea in ideas) / len(ideas)
        strength += max((ma - current_price) / current_price + (70 - rsi) / 100, 0.0)
        strength = max(min(strength, 1.0), 0.0)
        if strength <= 0:
            return
        await self.publish("signals", {"bot_id": self.bot_id, "strength": strength, "symbol": self.config.symbol})
        self.record_metric("signals", 1)

    async def on_evaluate(self) -> dict[str, float]:
        signals = self.performance_ledger.get_bot_summary(self.bot_id).get("signals", 0)
        return {"signals": float(signals)}

    async def on_terminate(self) -> None:
        if self._research_queue is not None:
            await self.unsubscribe("research", self._research_queue)
        self.logger.info("AnalystBot %s terminated", self.bot_id)
