"""Engine runtime orchestration."""
from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Any

from fastapi import FastAPI

from .ai import AIAssistant
from .config import get_settings
from .engine.clock import EngineClock
from .engine.fills import FillHistory, PaperFillModel
from .engine.market import MarketDataEngine
from .engine.portfolio import Portfolio
from .engine.simulator import PaperSimulator
from .engine.strategy import build_strategy
from .logging import get_logger
from .models.core import PriceTick
from .models.enums import OrderSide, SignalType
from .persistence.repo import Repository
from .services.state import StateService
from .services.stats import summarize
from .ws import ConnectionManager


class EngineRuntime:
    """Bundle engine components and coordinate async tasks."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.logger = get_logger(__name__)
        self.state_service = StateService()
        self.market_engine = MarketDataEngine(history_window=settings.history_window)
        self.strategy_engine = build_strategy(settings.default_aggression)
        self.clock = EngineClock(settings.tick_interval_ms)
        self.fill_model = PaperFillModel(
            maker_fee_bps=settings.maker_fee_bps,
            taker_fee_bps=settings.taker_fee_bps,
        )
        self.portfolio = self.state_service.state.portfolio
        self.simulator = PaperSimulator(self.portfolio, self.fill_model)
        self.repository = Repository()
        self.connection_manager = ConnectionManager()
        self.fill_history = FillHistory()
        self._last_tick: dict[str, PriceTick] = {}
        self._tasks: list[asyncio.Task[Any]] = []
        self._signal_queue: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self._stop = asyncio.Event()
        self._rng = random.Random(42)
        self.ai_assistant = AIAssistant(
            state_service=self.state_service,
            strategy_engine=self.strategy_engine,
            market_engine=self.market_engine,
            signal_queue=self._signal_queue,
        )

    async def startup(self, app: FastAPI) -> None:
        app.state.runtime = self
        await self.repository.initialize()
        self.logger.info("runtime initialized")
        self._stop.clear()
        await self.ai_assistant.start()
        self._tasks = [
            asyncio.create_task(self._market_task(), name="market_task"),
            asyncio.create_task(self._strategy_task(), name="strategy_task"),
            asyncio.create_task(self._execution_task(), name="execution_task"),
            asyncio.create_task(self._broadcast_task(), name="broadcast_task"),
        ]

    async def shutdown(self) -> None:
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        await self.ai_assistant.shutdown()
        self.logger.info("runtime stopped")

    async def _market_task(self) -> None:
        price = 40000.0
        volume = 1.0
        symbol = "XBT/USD"
        async for ts in self.clock.ticks():
            if self._stop.is_set():
                break
            price += self._rng.uniform(-5, 5)
            price = max(price, 1.0)
            volume = max(0.1, volume + self._rng.uniform(-0.05, 0.05))
            tick = PriceTick(symbol=symbol, price=price, volume=volume, ts=ts)
            self._last_tick[symbol] = tick
            await self.market_engine.ingest(tick)
            self.portfolio.mark_price(symbol, price)
            self.ai_assistant.record_market_tick(tick)
        self.clock.stop()

    async def _strategy_task(self) -> None:
        async for tick in self.market_engine.stream.stream():
            if self._stop.is_set():
                break
            signal = self.strategy_engine.on_tick(tick)
            try:
                self._signal_queue.put_nowait(signal)
            except asyncio.QueueFull:
                self.logger.warning("signal queue full; dropping signal")

    async def _execution_task(self) -> None:
        while not self._stop.is_set():
            signal = await self._signal_queue.get()
            if signal.signal == SignalType.FLAT:
                continue
            params = self.state_service.state.aggression
            last_tick = self._last_tick.get(signal.symbol)
            if last_tick is None:
                continue
            snapshot = self.portfolio.snapshot(signal.ts)
            notional = snapshot.total_equity * params.position_fraction
            if notional <= 0:
                continue
            size = max(0.0, notional / last_tick.price)
            if size == 0:
                continue
            side = OrderSide.BUY if signal.signal == SignalType.LONG else OrderSide.SELL
            if not self.state_service.risk.can_trade(
                portfolio=snapshot,
                symbol=signal.symbol,
                side=side,
                size=size,
                price=last_tick.price,
            ):
                self.logger.info("risk rejected trade", symbol=signal.symbol)
                continue
            position_before = self.portfolio.positions.get(signal.symbol)
            realized_before = position_before.realized_pnl if position_before else 0.0
            order = self.simulator.submit(
                symbol=signal.symbol,
                side=side,
                size=size,
                price=last_tick.price,
                order_type=params.order_type,
                aggression=params.aggression,
                mode=snapshot.mode,
            )
            fill = self.simulator.execute(order, last_tick)
            self.fill_history.record(fill)
            position_after = self.portfolio.positions.get(fill.symbol)
            realized_after = position_after.realized_pnl if position_after else 0.0
            pnl_change = realized_after - realized_before
            trade_value = fill.price * fill.size
            self.state_service.record_trade(pnl=pnl_change, trade_value=trade_value, is_maker=fill.maker)
            await self.repository.record_fill(fill)
            await self.connection_manager.broadcast(
                {
                    "channel": "trade",
                    "payload": {
                        "symbol": fill.symbol,
                        "price": fill.price,
                        "size": fill.size,
                        "side": fill.side.value,
                        "fee": fill.fee,
                    },
                    "ts": datetime.utcnow().isoformat(),
                }
            )

    async def _broadcast_task(self) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(1.0)
            snapshot = self.portfolio.snapshot(datetime.utcnow())
            stats_payload = summarize(snapshot, self.state_service.state.stats)
            await self.connection_manager.broadcast(
                {
                    "channel": "portfolio:update",
                    "payload": {
                        "cash": snapshot.cash,
                        "equity": snapshot.equity,
                        "pnl_realized": snapshot.pnl_realized,
                        "pnl_unrealized": snapshot.pnl_unrealized,
                        "total_equity": snapshot.total_equity,
                    },
                    "ts": datetime.utcnow().isoformat(),
                }
            )
            await self.connection_manager.broadcast(
                {
                    "channel": "stats:update",
                    "payload": stats_payload,
                    "ts": datetime.utcnow().isoformat(),
                }
            )

    def history(self, symbol: str) -> list[PriceTick]:
        return self.market_engine.stream.history(symbol)

    def aggregated_state(self) -> dict[str, Any]:
        snapshot = self.portfolio.snapshot(datetime.utcnow())
        stats_payload = summarize(snapshot, self.state_service.state.stats)
        return {
            "portfolio": snapshot.model_dump(),
            "stats": stats_payload,
            "aggression": self.state_service.state.aggression.model_dump(),
        }
