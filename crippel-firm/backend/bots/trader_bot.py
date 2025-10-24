"""Trader bot executing analyst signals."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

from ..engine.execution import ExecutionEngine, OrderIntent, Signal
from ..engine.params import StrategyParams, tune_params
from ..engine.portfolio import Portfolio
from ..engine.simulator import SimulatedMarketData
from ..engine.kraken_adapter import KrakenAdapter
from ..firm.economy import PerformanceLedger
from ..firm.interfaces import MetricDict
from ..logging import get_logger
from ..settings import RiskSettings
from .base import WorkerBot


@dataclass
class TraderConfig:
    symbol: str = "BTC-USD"
    aggression: int = 5
    mode: str = "paper"


class TraderBot(WorkerBot):
    bot_type = "trader"

    def __init__(
        self,
        event_bus,
        ledger: PerformanceLedger,
        portfolio: Portfolio,
        market_data: SimulatedMarketData,
        risk: RiskSettings,
        config: TraderConfig | None = None,
        adapter: Optional[KrakenAdapter] = None,
    ) -> None:
        super().__init__(event_bus=event_bus, ledger=ledger)
        self.config = config or TraderConfig()
        self.params: StrategyParams = tune_params(self.config.aggression)
        self.execution = ExecutionEngine(portfolio=portfolio, params=self.params)
        self.portfolio = portfolio
        self.market_data = market_data
        self.risk_settings = risk
        self.adapter = adapter or KrakenAdapter()
        self._signals_queue: Optional[asyncio.Queue] = None
        self._responses_queue: Optional[asyncio.Queue] = None
        self._halt_queue: Optional[asyncio.Queue] = None
        self._trades = 0
        self._logger = get_logger("bot.trader", bot_id=self.bot_id)

    async def on_start(self) -> None:
        self._signals_queue = await self.subscribe("signals")
        self._responses_queue = await self.subscribe("orders:response")
        self._halt_queue = await self.subscribe("risk:halt")

    async def on_tick(self) -> None:
        assert self._signals_queue is not None
        if self._halt_queue is not None:
            while True:
                try:
                    halt = self._halt_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    self._logger.warning("risk_halt", payload=halt)
                    self.record_metric("policy_adherence", 0.0)
                    await asyncio.sleep(0.2)
                    return
        try:
            signal_payload = self._signals_queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.1)
            return
        signal = Signal(
            symbol=signal_payload["symbol"],
            confidence=signal_payload.get("strength", 0.0),
            price=signal_payload.get("price", self.market_data.current_price(signal_payload["symbol"])),
            reason=signal_payload.get("reason", ""),
            latency_ms=(time.time() - signal_payload.get("ts", time.time())) * 1000,
        )
        intent = self.execution.plan(signal)
        if not intent:
            return
        approved = await self._request_risk_approval(intent, signal_payload)
        if not approved:
            self.record_metric("policy_adherence", 0.0)
            return
        await self._execute(intent, signal_payload)

    async def _request_risk_approval(self, intent: OrderIntent, payload: dict) -> bool:
        assert self._responses_queue is not None
        request = {
            "order_id": intent.order_id,
            "symbol": intent.symbol,
            "side": intent.side,
            "quantity": intent.quantity,
            "price": intent.price,
            "bot_id": self.bot_id,
            "origin_bot": payload.get("bot_id"),
        }
        await self.publish("orders:intent", request)
        start = time.time()
        while time.time() - start < 3.0:
            try:
                response = self._responses_queue.get_nowait()
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.05)
                continue
            if response.get("order_id") != intent.order_id:
                continue
            return bool(response.get("approved", False))
        return False

    async def _execute(self, intent: OrderIntent, payload: dict) -> None:
        price = intent.price
        symbol = intent.symbol
        if self.config.mode == "live":
            if intent.side == "BUY":
                await self.adapter.buy(symbol, intent.quantity, price)
            else:
                await self.adapter.sell(symbol, intent.quantity, price)
            fill = {
                "bot_id": payload.get("bot_id"),
                "trader_id": self.bot_id,
                "symbol": symbol,
                "side": intent.side,
                "quantity": intent.quantity,
                "price": price,
                "fees": 0.0,
                "mode": "live",
            }
        else:
            self.market_data.advance_time()
            price = self.market_data.current_price(symbol)
            liquidity = "taker"
            fill_info = self.portfolio.apply_fill(symbol, intent.side, intent.quantity, price, liquidity=liquidity)
            fill = {
                "bot_id": payload.get("bot_id"),
                "trader_id": self.bot_id,
                "symbol": symbol,
                "side": intent.side,
                "quantity": intent.quantity,
                "price": price,
                "fees": fill_info["fee"],
                "mode": "paper",
            }
        self._trades += 1
        self.record_metric("trades", float(self._trades))
        self.record_metric("policy_adherence", 1.0)
        await self.publish("orders:fill", fill)

    async def on_evaluate(self) -> MetricDict:
        exposure = self.portfolio.current_exposure_value
        equity = self.portfolio.total_equity()
        metrics: MetricDict = {
            "delta_realized_pnl": self.portfolio.realized_pnl,
            "avg_exposure": exposure / equity if equity else 0.0,
            "policy_adherence": self.ledger.fetch(self.bot_id).get("policy_adherence", 1.0),
            "decision_latency_ms": 0.0,
        }
        return metrics

    async def on_terminate(self) -> None:
        if self._signals_queue is not None:
            await self.unsubscribe("signals", self._signals_queue)
        if self._responses_queue is not None:
            await self.unsubscribe("orders:response", self._responses_queue)
        if self._halt_queue is not None:
            await self.unsubscribe("risk:halt", self._halt_queue)
        await self.adapter.close()
