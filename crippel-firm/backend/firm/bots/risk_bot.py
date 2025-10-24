"""Risk bot implementation."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from ..config import CapitalPolicy
from ..engine.portfolio import Portfolio
from ..utils.metrics import PerformanceLedger
from .base import WorkerBot


@dataclass
class RiskConfig:
    capital_policy: CapitalPolicy
    check_interval: float = 3.0


class RiskBot(WorkerBot):
    """Monitors portfolio risk and vetoes excessive orders."""

    def __init__(
        self,
        event_bus,
        performance_ledger: PerformanceLedger,
        portfolio: Portfolio,
        config: RiskConfig,
    ) -> None:
        super().__init__(event_bus=event_bus, performance_ledger=performance_ledger, bot_type="risk")
        self.config = config
        self.portfolio = portfolio
        self._order_queue: Optional[asyncio.Queue[dict[str, object]]] = None

    async def on_start(self) -> None:
        self._order_queue = await self.subscribe("orders")
        self.logger.info("RiskBot %s started", self.bot_id)

    async def on_tick(self) -> None:
        assert self._order_queue is not None
        try:
            order_event = self._order_queue.get_nowait()
        except asyncio.QueueEmpty:
            order_event = None
        if order_event:
            order = order_event.get("order", {})
            exposure = self.portfolio.current_exposure()
            if exposure > self.config.capital_policy.max_position_usd:
                await self.publish("risk_alerts", {"bot_id": self.bot_id, "order": order, "reason": "exposure"})
                self.record_metric("alerts", 1)
        await asyncio.sleep(self.config.check_interval)

    async def on_evaluate(self) -> dict[str, float]:
        alerts = self.performance_ledger.get_bot_summary(self.bot_id).get("alerts", 0)
        exposure = self.portfolio.current_exposure()
        return {"alerts": float(alerts), "exposure": exposure}

    async def on_terminate(self) -> None:
        if self._order_queue is not None:
            await self.unsubscribe("orders", self._order_queue)
        self.logger.info("RiskBot %s terminated", self.bot_id)
