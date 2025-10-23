"""Live trading simulator backed by asynchronous worker loops."""

from __future__ import annotations

import asyncio
import random
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from ..utils.indicators import normalize_number
from ..utils.logger import get_child
from .integrations.kraken import KrakenClient

logger = get_child("live")

DEFAULT_INTERVAL_MS = 5000
DEFAULT_CAPITAL = 100_000

SYMBOL_POOL = [
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "MATIC/USD",
    "ATOM/USD",
    "DOGE/USD",
]

WORKER_PROFILES = [
    {"id": "worker-alpha", "name": "Alpha Worker", "focus": "High-frequency momentum"},
    {"id": "worker-beta", "name": "Beta Worker", "focus": "Mean reversion scalps"},
    {"id": "worker-gamma", "name": "Gamma Worker", "focus": "Liquidity sweeps"},
    {"id": "worker-delta", "name": "Delta Worker", "focus": "Funding arbitrage"},
]

EventHandler = Callable[[Any], Any]


class LiveTradingService:
    def __init__(self, interval_ms: int = DEFAULT_INTERVAL_MS, capital: float = DEFAULT_CAPITAL) -> None:
        self.interval_ms = interval_ms
        self.interval_seconds = interval_ms / 1000
        self.initial_capital = capital
        self.cash = capital
        self.realized_pnl = 0.0
        self.position_book: Dict[str, Dict[str, float]] = {}
        self.trades: List[Dict[str, Any]] = []
        self.pl_history: List[Dict[str, Any]] = []
        self.research_notes: List[Dict[str, Any]] = []

        self.brain = {
            "name": "Brain Bot",
            "status": "initializing",
            "directives": [
                "Stabilize exposure across worker cohorts",
                "Favor high Sharpe strategies under 2% slippage tolerance",
            ],
            "researchFocus": "Watching macro liquidity shifts",
        }

        self.workers = [
            {
                **profile,
                "status": "warming",
                "confidence": 0.0,
                "lastSignal": None,
                "pendingTasks": 0,
            }
            for profile in WORKER_PROFILES
        ]

        self.executor = {
            "status": "idle",
            "lastDecision": None,
            "lastOrderReference": None,
            "mode": "simulation",
        }

        self.kraken_client = KrakenClient()
        if self.kraken_client.enabled:
            self.executor["mode"] = "live"

        self._listeners: Dict[str, List[EventHandler]] = defaultdict(list)
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self.snapshot: Optional[Dict[str, Any]] = None

    def on(self, event: str, handler: EventHandler) -> None:
        self._listeners[event].append(handler)

    def off(self, event: str, handler: EventHandler) -> None:
        if handler in self._listeners.get(event, []):
            self._listeners[event].remove(handler)

    def _emit(self, event: str, payload: Any) -> None:
        if not self._loop:
            return
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        for handler in list(self._listeners.get(event, [])):
            try:
                result = handler(payload)
                if asyncio.iscoroutine(result):
                    if running_loop and running_loop is self._loop:
                        asyncio.create_task(result)
                    else:
                        asyncio.run_coroutine_threadsafe(result, self._loop)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Live service handler failure", exc_info=exc)

    async def start(self) -> None:
        if self._task:
            return
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._task = asyncio.create_task(self._run())
        await self.tick()  # prime state for immediate responses

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._loop = None

    async def _run(self) -> None:
        while self._running:
            start = asyncio.get_running_loop().time()
            await self.tick()
            elapsed = asyncio.get_running_loop().time() - start
            await asyncio.sleep(max(0.0, self.interval_seconds - elapsed))

    async def tick(self) -> None:
        self.update_brain_state()
        self.generate_research_insight()

        worker_tasks = []
        for worker in self.workers:
            self.update_worker_state(worker)
            if random.random() < 0.35:
                worker_tasks.append(self.generate_worker_trade(worker))
        if worker_tasks:
            await asyncio.gather(*worker_tasks, return_exceptions=True)

        self.capture_snapshot()
        self.emit_update()

    def update_brain_state(self) -> None:
        active_signals = [f"{trade['symbol']} {trade['side']} {trade['quantity']}" for trade in self.trades[:5]]
        self.brain = {
            **self.brain,
            "status": "coordinating execution" if active_signals else "monitoring",
            "activeSignals": active_signals,
        }

    def generate_research_insight(self) -> None:
        authors = ["Quant Ops", "Market Intelligence", "Macro Desk", "On-chain Insights"]
        themes = [
            "funding spreads tightening across majors",
            "elevated perp open interest versus spot",
            "macro dollar weakness supporting risk assets",
            "volatility compression indicating breakout setup",
            "options skew rotating bullish on 1w tenors",
        ]
        catalysts = [
            "Asian session liquidity window",
            "incoming CPI release",
            "Fed speakers in focus",
            "large on-chain transfer cluster",
            "derivatives expiry roll",
        ]
        note = {
            "id": str(uuid4()),
            "author": random.choice(authors),
            "theme": random.choice(themes),
            "catalyst": random.choice(catalysts),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.research_notes.insert(0, note)
        if len(self.research_notes) > 30:
            self.research_notes = self.research_notes[:30]

    def update_worker_state(self, worker: Dict[str, Any]) -> None:
        phase = random.random()
        if phase > 0.75:
            worker["status"] = "deploying signal"
        elif phase > 0.4:
            worker["status"] = "scanning"
        else:
            worker["status"] = "refining"
        worker["confidence"] = normalize_number(random.uniform(50, 99), 2)
        worker["pendingTasks"] = int(random.random() * 3)

    async def generate_worker_trade(self, worker: Dict[str, Any]) -> None:
        symbol = random.choice(SYMBOL_POOL)
        side = "buy" if random.random() > 0.5 else "sell"
        quantity = normalize_number(random.uniform(0.5, 3.5), 3)
        price_base = random.uniform(0.98, 1.02) if side == "buy" else random.uniform(0.96, 1.04)
        price = normalize_number(self.resolve_reference_price(symbol) * price_base, 2)
        confidence = normalize_number(random.uniform(55, 92), 2)
        narrative = (
            "Worker expects continuation after liquidity sweep"
            if side == "buy"
            else "Worker sees exhaustion and looks to mean revert"
        )
        worker["lastSignal"] = {
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "narrative": narrative,
        }
        await self.submit_worker_trade(
            {
                "workerId": worker["id"],
                "workerName": worker["name"],
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "confidence": confidence,
                "narrative": narrative,
            }
        )

    def resolve_reference_price(self, symbol: str) -> float:
        base = {
            "BTC/USD": 68_000,
            "ETH/USD": 3_500,
            "SOL/USD": 150,
            "MATIC/USD": 0.95,
            "ATOM/USD": 12,
            "DOGE/USD": 0.15,
        }
        return base.get(symbol, 100.0)

    async def submit_worker_trade(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        worker_id = trade_request.get("workerId")
        symbol = trade_request.get("symbol")
        side = trade_request.get("side")
        quantity = float(trade_request.get("quantity", 0))
        price = float(trade_request.get("price", 0))
        if not symbol or not side or not quantity or not price:
            raise ValueError("Trade request missing required fields")

        request_id = str(uuid4())
        self.executor["status"] = "evaluating"
        decision = {
            "requestId": request_id,
            "workerId": worker_id,
            "workerName": trade_request.get("workerName"),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "confidence": trade_request.get("confidence"),
            "narrative": trade_request.get("narrative"),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.executor["lastDecision"] = decision

        execution = await self.kraken_client.submit_order(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "meta": {"requestId": request_id, "workerId": worker_id},
            }
        )
        self.executor["lastOrderReference"] = execution.get("reference")
        trade = await self.record_trade(
            {
                "id": request_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "confidence": trade_request.get("confidence"),
                "workerId": worker_id,
                "workerName": trade_request.get("workerName"),
                "narrative": trade_request.get("narrative"),
                "execution": execution,
            }
        )
        self.executor["status"] = "idle"
        self.emit_update()
        return trade

    async def record_trade(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.utcnow().isoformat()
        trade = {
            **payload,
            "timestamp": timestamp,
        }
        self.trades.insert(0, trade)
        if len(self.trades) > 200:
            self.trades = self.trades[:200]
        self.update_positions(trade)
        self.capture_snapshot()
        return trade

    def update_positions(self, trade: Dict[str, Any]) -> None:
        symbol = trade["symbol"]
        side = trade["side"]
        quantity = trade["quantity"]
        price = trade["price"]
        signed_quantity = quantity if side == "buy" else -quantity
        value = price * quantity
        if side == "buy":
            self.cash -= value
        else:
            self.cash += value

        position = self.position_book.get(symbol, {"symbol": symbol, "quantity": 0.0, "avgPrice": 0.0, "lastPrice": price})
        previous_quantity = position["quantity"]
        previous_avg = position["avgPrice"]
        realized = 0.0

        if previous_quantity == 0 or (previous_quantity > 0 and signed_quantity > 0) or (previous_quantity < 0 and signed_quantity < 0):
            total_quantity = abs(previous_quantity) + abs(signed_quantity)
            weighted_price = abs(previous_quantity) * previous_avg + abs(signed_quantity) * price
            new_quantity = previous_quantity + signed_quantity
            position["quantity"] = round(new_quantity, 6)
            position["avgPrice"] = 0.0 if total_quantity == 0 else round(weighted_price / total_quantity, 6)
        else:
            closing_quantity = min(abs(previous_quantity), abs(signed_quantity))
            realized = closing_quantity * (price - previous_avg) * (1 if previous_quantity > 0 else -1)
            residual = abs(signed_quantity) - closing_quantity
            next_quantity = previous_quantity + signed_quantity
            if abs(previous_quantity) > abs(signed_quantity):
                position["quantity"] = round(next_quantity, 6)
                position["avgPrice"] = previous_avg if position["quantity"] != 0 else 0.0
            elif residual > 0:
                direction = 1 if signed_quantity > 0 else -1
                position["quantity"] = round(direction * residual, 6)
                position["avgPrice"] = round(price, 6)
            else:
                position["quantity"] = 0.0
                position["avgPrice"] = 0.0

        position["lastPrice"] = price
        if abs(position["quantity"]) < 1e-8:
            self.position_book.pop(symbol, None)
        else:
            self.position_book[symbol] = position

        self.realized_pnl += realized

    def capture_snapshot(self) -> None:
        timestamp = datetime.utcnow().isoformat()
        open_positions = []
        for position in self.position_book.values():
            unrealized = (position["lastPrice"] - position["avgPrice"]) * position["quantity"]
            open_positions.append(
                {
                    "symbol": position["symbol"],
                    "quantity": normalize_number(position["quantity"], 4),
                    "avgPrice": normalize_number(position["avgPrice"], 4),
                    "lastPrice": normalize_number(position["lastPrice"], 4),
                    "direction": "long" if position["quantity"] >= 0 else "short",
                    "unrealizedPnl": normalize_number(unrealized, 2),
                }
            )

        total_unrealized = sum(item["unrealizedPnl"] for item in open_positions)
        equity = self.cash + sum(item["lastPrice"] * item["quantity"] for item in open_positions)

        self.pl_history.append(
            {
                "timestamp": timestamp,
                "equity": normalize_number(equity, 2),
                "realized": normalize_number(self.realized_pnl, 2),
                "unrealized": normalize_number(total_unrealized, 2),
            }
        )
        if len(self.pl_history) > 720:
            self.pl_history.pop(0)

        self.snapshot = {
            "timestamp": timestamp,
            "openPositions": open_positions,
            "equity": equity,
            "cash": self.cash,
            "realizedPnL": self.realized_pnl,
            "unrealizedPnL": total_unrealized,
        }

    def emit_update(self) -> None:
        self._emit("update", {"type": "live:update", "state": self.get_state()})

    def get_state(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "brain": self.brain,
            "research": self.research_notes,
            "workers": self.workers,
            "executor": self.executor,
            "trades": self.trades,
            "openPositions": self.snapshot.get("openPositions", []) if self.snapshot else [],
            "performance": self.pl_history,
            "capital": {
                "initial": self.initial_capital,
                "cash": normalize_number(self.cash, 2),
                "realizedPnL": normalize_number(self.realized_pnl, 2),
                "unrealizedPnL": normalize_number((self.snapshot or {}).get("unrealizedPnL", 0), 2),
                "equity": normalize_number((self.snapshot or {}).get("equity", self.initial_capital), 2),
            },
        }

    def add_research_insight(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        note = {
            "id": str(uuid4()),
            "author": payload.get("author") or "Research Desk",
            "theme": payload.get("theme") or "General market observation",
            "catalyst": payload.get("catalyst") or "Operator supplied",
            "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
        }
        self.research_notes.insert(0, note)
        if len(self.research_notes) > 30:
            self.research_notes = self.research_notes[:30]
        self.emit_update()
        return note


__all__ = ["LiveTradingService"]
