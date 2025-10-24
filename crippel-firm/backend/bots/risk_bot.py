"""Risk bot enforcing exposure and drawdown constraints."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

from ..engine.portfolio import Portfolio
from ..firm.economy import PerformanceLedger
from ..logging import get_logger
from ..settings import RiskSettings
from .base import WorkerBot


@dataclass
class RiskConfig:
    settings: RiskSettings


class RiskBot(WorkerBot):
    bot_type = "risk"

    def __init__(
        self,
        event_bus,
        ledger: PerformanceLedger,
        portfolio: Portfolio,
        config: RiskConfig,
    ) -> None:
        super().__init__(event_bus=event_bus, ledger=ledger)
        self.portfolio = portfolio
        self.config = config
        self._intent_queue: Optional[asyncio.Queue] = None
        self._peak_equity = portfolio.total_equity()
        self._logger = get_logger("bot.risk", bot_id=self.bot_id)

    async def on_start(self) -> None:
        self._intent_queue = await self.subscribe("orders:intent")

    async def on_tick(self) -> None:
        assert self._intent_queue is not None
        try:
            intent = self._intent_queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.1)
            self._update_drawdown()
            return
        approved = self._assess_intent(intent)
        response = {"order_id": intent["order_id"], "approved": approved}
        await self.publish("orders:response", response)
        self.record_metric("approvals", 1.0 if approved else 0.0)

    def _assess_intent(self, intent: dict) -> bool:
        symbol = intent["symbol"]
        side = intent["side"]
        quantity = intent["quantity"]
        price = intent["price"]
        if quantity <= 0:
            return False
        current_equity = self.portfolio.total_equity()
        exposure = self.portfolio.current_exposure_value
        symbol_position = self.portfolio.position(symbol)
        symbol_quantity = symbol_position.quantity if symbol_position else 0.0
        symbol_price = self.portfolio._marks.get(symbol, price)  # type: ignore[attr-defined]
        symbol_value = symbol_quantity * symbol_price
        total_exposure_limit = self.config.settings.max_total_exposure * current_equity
        symbol_exposure_limit = self.config.settings.max_symbol_exposure * current_equity
        if side == "BUY":
            new_exposure = exposure + quantity * price
            new_symbol_value = symbol_value + quantity * price
        else:
            new_exposure = exposure - min(symbol_value, quantity * price)
            new_symbol_value = max(0.0, symbol_value - quantity * price)
        if new_exposure > total_exposure_limit:
            self._logger.warning("exposure_limit", new_exposure=new_exposure, limit=total_exposure_limit)
            return False
        if new_symbol_value > symbol_exposure_limit:
            self._logger.warning("symbol_limit", symbol=symbol, value=new_symbol_value, limit=symbol_exposure_limit)
            return False
        if self._current_drawdown(current_equity) >= self.config.settings.kill_switch_drawdown:
            self._logger.error("kill_switch_triggered")
            return False
        return True

    def _current_drawdown(self, equity: float) -> float:
        if equity <= 0:
            return 1.0
        if equity > self._peak_equity:
            self._peak_equity = equity
            return 0.0
        return (self._peak_equity - equity) / self._peak_equity if self._peak_equity else 0.0

    def _update_drawdown(self) -> None:
        equity = self.portfolio.total_equity()
        drawdown = self._current_drawdown(equity)
        if drawdown >= self.config.settings.max_drawdown:
            self._logger.warning("drawdown_alert", drawdown=drawdown)
            payload = {"ts": time.time(), "drawdown": drawdown}
            asyncio.create_task(self.publish("risk:halt", payload))

    async def on_evaluate(self) -> dict[str, float]:
        equity = self.portfolio.total_equity()
        drawdown = self._current_drawdown(equity)
        metrics = {
            "policy_adherence": 1.0 - min(drawdown / self.config.settings.max_drawdown if self.config.settings.max_drawdown else 1.0, 1.0),
            "decision_latency_ms": 0.0,
        }
        return metrics

    async def on_terminate(self) -> None:
        if self._intent_queue is not None:
            await self.unsubscribe("orders:intent", self._intent_queue)
