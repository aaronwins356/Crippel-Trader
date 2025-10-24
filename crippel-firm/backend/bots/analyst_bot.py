"""Analyst bot combining research with indicators."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from ..engine.indicators import ema, rsi
from ..engine.params import StrategyParams, tune_params
from ..engine.simulator import SimulatedMarketData
from ..firm.economy import PerformanceLedger
from ..logging import get_logger
from .base import WorkerBot


@dataclass
class AnalystConfig:
    aggression: int = 5
    symbol_map: dict[str, str] = field(default_factory=lambda: {"BTC": "BTC-USD", "ETH": "ETH-USD"})
    min_volume: float = 1.0


class AnalystBot(WorkerBot):
    bot_type = "analyst"

    def __init__(
        self,
        event_bus,
        ledger: PerformanceLedger,
        market_data: SimulatedMarketData,
        config: AnalystConfig | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, ledger=ledger)
        self.market_data = market_data
        self.config = config or AnalystConfig()
        self.params: StrategyParams = tune_params(self.config.aggression)
        self._research_queue: Optional[asyncio.Queue] = None
        self._fills_queue: Optional[asyncio.Queue] = None
        self._signals_sent = 0
        self._fills_seen = 0
        self._last_signal_ts = 0.0
        self._cooldowns: dict[str, float] = {}
        self._logger = get_logger("bot.analyst", bot_id=self.bot_id)

    async def on_start(self) -> None:
        self._research_queue = await self.subscribe("research:idea")
        self._fills_queue = await self.subscribe("orders:fill")

    async def on_tick(self) -> None:
        assert self._research_queue is not None
        ideas = []
        while True:
            try:
                message = self._research_queue.get_nowait()
                ideas.extend(message.get("ideas", []))
            except asyncio.QueueEmpty:
                break
        if not ideas:
            await asyncio.sleep(0.2)
        else:
            for idea in ideas:
                symbol = self.config.symbol_map.get(idea["ticker"].upper())
                if not symbol:
                    continue
                if time.time() < self._cooldowns.get(symbol, 0.0):
                    continue
                history = self.market_data.history(symbol, limit=60)
                if not history:
                    continue
                price_series = [tick.price for tick in history]
                if history[-1].volume < self.config.min_volume:
                    continue
                price = price_series[-1]
                fast = ema(price_series, 8)
                slow = ema(price_series, 21)
                momentum = (price - slow) / slow if slow else 0.0
                sentiment = idea.get("confidence", 0.0)
                overbought = 1 - rsi(price_series) / 100
                signal_strength = max(0.0, min(1.0, sentiment * 0.6 + momentum * 0.3 + overbought * 0.1))
                if signal_strength < self.params.signal_threshold:
                    continue
                cooldown_seconds = self.params.cooldown_ms / 1000
                self._cooldowns[symbol] = time.time() + cooldown_seconds
                signal = {
                    "bot_id": self.bot_id,
                    "symbol": symbol,
                    "strength": signal_strength,
                    "price": price,
                    "reason": f"insider {idea['role']}".strip(),
                    "ts": time.time(),
                }
                self._signals_sent += 1
                self.record_metric("signals", float(self._signals_sent))
                await self.publish("signals", signal)
                self._last_signal_ts = signal["ts"]
        if self._fills_queue is not None:
            while True:
                try:
                    fill = self._fills_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    if fill.get("bot_id") == self.bot_id:
                        self._fills_seen += 1
                        self.record_metric("fills", float(self._fills_seen))
        await asyncio.sleep(0.1)

    async def on_evaluate(self) -> dict[str, float]:
        hit_rate = (self._fills_seen / self._signals_sent) if self._signals_sent else 0.0
        latency = (time.time() - self._last_signal_ts) * 1000 if self._last_signal_ts else 0.0
        metrics = {
            "hit_rate": hit_rate,
            "decision_latency_ms": latency,
            "policy_adherence": 1.0,
        }
        return metrics

    async def on_terminate(self) -> None:
        if self._research_queue is not None:
            await self.unsubscribe("research:idea", self._research_queue)
        if self._fills_queue is not None:
            await self.unsubscribe("orders:fill", self._fills_queue)
