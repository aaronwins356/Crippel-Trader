"""Core runtime wiring feed -> strategy -> risk -> execution."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, Optional

from ..bus import EventBus
from ..config import Settings
from ..data.features import FeaturePipeline, LiveFeatureState
from ..models.types import Metrics, Position, Tick
from ..risk.risk_manager import RiskError, RiskManager
from ..storage.datastore import DataStore
from ..storage.model_registry import ModelRegistry
from ..strategy.base import BaseStrategy
from ..exec.broker_base import Broker
from ..runtime.metrics import MetricsCollector


class Engine:
    def __init__(
        self,
        settings: Settings,
        *,
        feed,
        strategy: BaseStrategy,
        broker: Broker,
        risk: RiskManager,
        datastore: DataStore,
        metrics: MetricsCollector,
        bus: EventBus,
        feature_pipeline: FeaturePipeline,
        model_registry: Optional[ModelRegistry] = None,
    ) -> None:
        self.settings = settings
        self.feed = feed
        self.strategy = strategy
        self.broker = broker
        self.risk = risk
        self.datastore = datastore
        self.metrics = metrics
        self.bus = bus
        self.model_registry = model_registry
        self.feature_state = LiveFeatureState(feature_pipeline, max_length=feature_pipeline.slow_window * 4)
        self._tick_queue: asyncio.Queue[Tick] = asyncio.Queue(maxsize=4096)
        self._tasks: list[asyncio.Task[Any]] = []
        self._running = False
        self._lock = asyncio.Lock()
        self._active_model_path: Optional[str] = None

    async def start(self) -> None:
        async with self._lock:
            if self._running:
                return
            self._running = True
            await self.feed.connect()
            self._tasks = [
                asyncio.create_task(self._run_feed(), name="croc-feed"),
                asyncio.create_task(self._run_pipeline(), name="croc-pipeline"),
            ]

    async def stop(self) -> None:
        async with self._lock:
            if not self._running:
                return
            self._running = False
            await self.feed.disconnect()
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

    async def _run_feed(self) -> None:
        try:
            async for tick in self.feed.stream():
                if hasattr(self.broker, "update_mark"):
                    self.broker.update_mark(tick.mid)  # type: ignore[attr-defined]
                try:
                    self._tick_queue.put_nowait(tick)
                except asyncio.QueueFull:
                    await self._tick_queue.put(tick)
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            pass

    async def _run_pipeline(self) -> None:
        try:
            while self._running:
                tick = await self._tick_queue.get()
                self.datastore.append_tick(tick)
                await self.bus.publish("ticks", tick.model_dump())
                await self.metrics.record_tick(tick)
                features = self.feature_state.update(tick)
                if features is None:
                    continue
                position = self.risk.positions.get(tick.symbol, Position(symbol=tick.symbol))
                order = await self.strategy.on_tick(tick, features, position)
                if order is None:
                    continue
                try:
                    self.risk.check_order(order, tick.mid)
                except RiskError as exc:
                    await self.bus.publish("alerts", {"type": "risk", "message": str(exc)})
                    continue
                latency_start = perf_counter()
                fill = await self.broker.submit(order)
                latency_ms = (perf_counter() - latency_start) * 1000
                position = self.risk.update_fill(fill)
                await self.strategy.on_fill(fill, position)
                await self.metrics.record_fill(fill, position.size, self.risk.state.max_drawdown, latency_ms)
                self.datastore.append_fill(fill)
                await self.bus.publish("fills", fill.model_dump())
                metrics = await self.metrics.snapshot()
                self.datastore.append_metrics(metrics)
                await self.bus.publish("metrics", metrics.model_dump())
                self._maybe_reload_policy()
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            pass

    def _maybe_reload_policy(self) -> None:
        if not self.model_registry or not hasattr(self.strategy, "reload"):
            return
        active = self.model_registry.active_model()
        if active is None:
            return
        resolved = str(active)
        if resolved == self._active_model_path:
            return
        self.strategy.reload(active)
        self._active_model_path = resolved

    @property
    def running(self) -> bool:
        return self._running

    async def metrics_snapshot(self) -> Metrics:
        return await self.metrics.snapshot()


__all__ = ["Engine"]
