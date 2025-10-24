"""Trader bot implementation."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from ..engine.kraken_adapter import KrakenAdapter
from ..engine.portfolio import Portfolio
from ..engine.simulator import SimulatedMarketData
from ..utils.logging import get_logger
from ..utils.metrics import PerformanceLedger
from .base import WorkerBot


@dataclass
class TraderConfig:
    symbol: str = "BTC/USD"
    tick_interval: float = 2.0


class TraderBot(WorkerBot):
    """Simple trader consuming signals from analyst bots."""

    def __init__(
        self,
        event_bus,
        performance_ledger: PerformanceLedger,
        portfolio: Portfolio,
        adapter: KrakenAdapter,
        market_data: SimulatedMarketData,
        config: Optional[TraderConfig] = None,
    ) -> None:
        super().__init__(event_bus=event_bus, performance_ledger=performance_ledger, bot_type="trader")
        self.config = config or TraderConfig()
        self.portfolio = portfolio
        self.adapter = adapter
        self.market_data = market_data
        self._signal_queue: Optional[asyncio.Queue[dict[str, float]]] = None
        self.logger = get_logger("bot.trader")

    async def on_start(self) -> None:
        self._signal_queue = await self.subscribe("signals")
        self.logger.info("TraderBot %s started", self.bot_id)

    async def on_tick(self) -> None:
        assert self._signal_queue is not None
        try:
            signal = self._signal_queue.get_nowait()
        except asyncio.QueueEmpty:
            signal = None
        if signal:
            strength = signal.get("strength", 0.0)
            if strength <= 0:
                return
            price = self.market_data.current_price(self.config.symbol)
            quantity = self.portfolio.calculate_order_size(price, strength)
            if quantity <= 0:
                return
            order = await self.adapter.buy(self.config.symbol, quantity, price)
            self.portfolio.apply_fill(order)
            self.record_metric("trades", 1)
            await self.publish("orders", {"bot_id": self.bot_id, "order": order})

    async def on_evaluate(self) -> dict[str, float]:
        pnl = self.portfolio.realized_pnl + self.portfolio.unrealized_pnl(self.market_data)
        metrics = {"pnl": pnl, "trades": self.performance_ledger.get_bot_summary(self.bot_id).get("trades", 0)}
        self.logger.debug("Evaluation metrics: %s", metrics)
        return metrics

    async def on_terminate(self) -> None:
        if self._signal_queue is not None:
            await self.unsubscribe("signals", self._signal_queue)
        self.logger.info("TraderBot %s terminated", self.bot_id)
