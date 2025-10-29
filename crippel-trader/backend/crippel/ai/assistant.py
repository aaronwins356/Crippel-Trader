"""High level orchestration for the Croc-Bot AI assistant."""
from __future__ import annotations

import asyncio
import contextlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from ..ai_local import AI_BACKEND, chat as local_chat, get_backend_descriptor
from ..config import get_settings
from ..engine.market import MarketDataEngine
from ..engine.strategy import StrategyEngine
from ..logging import get_logger
from ..models.core import PriceTick, Signal
from ..models.enums import SignalType
from ..services.state import StateService
from .decision_log import DecisionLogger
from .research import WebResearcher
from .schemas import AssistantDecision, ResearchItem, TradeRecommendation


class AIAssistant:
    """Coordinates strategy generation, research, and trade execution via on-device models."""

    def __init__(
        self,
        *,
        state_service: StateService,
        strategy_engine: StrategyEngine,
        market_engine: MarketDataEngine,
        signal_queue: asyncio.Queue[Signal] | None = None,
    ) -> None:
        self._settings = get_settings()
        self._state_service = state_service
        self._strategy_engine = strategy_engine
        self._market_engine = market_engine
        self._signal_queue = signal_queue
        self._logger = get_logger(__name__)
        self._decision_logger = DecisionLogger(
            self._settings.project_root / "logs" / "ai_decisions.log"
        )
        self._researcher = WebResearcher(timeout=min(15.0, self._settings.ai_request_timeout))
        self._decision_interval = self._settings.ai_decision_interval_seconds
        self._max_trades = self._settings.ai_max_trades_per_cycle
        self._history_window = self._settings.ai_history_window
        self._stop = asyncio.Event()
        self._task: asyncio.Task[Any] | None = None
        self._last_ticks: dict[str, PriceTick] = {}
        self._last_decision: AssistantDecision | None = None

    def record_market_tick(self, tick: PriceTick) -> None:
        """Track the most recent tick for each symbol for decision context."""
        self._last_ticks[tick.symbol] = tick

    async def start(self) -> None:
        if self._task is not None:
            return
        await self._decision_logger.log_event(
            "assistant_start",
            {"backend": AI_BACKEND, "descriptor": get_backend_descriptor()},
        )
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name="ai_assistant_loop")

    async def shutdown(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._researcher.aclose()
        await self._decision_logger.log_event("assistant_stop", {})

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._evaluate_and_act()
            except Exception as exc:  # pragma: no cover - defensive logging
                self._logger.exception("ai evaluation failed", error=str(exc))
                await self._decision_logger.log_event(
                    "error",
                    {"message": str(exc)},
                )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._decision_interval)
            except asyncio.TimeoutError:
                continue

    async def _evaluate_and_act(self) -> None:
        market_snapshot = self._summarize_market()
        portfolio_snapshot = self._state_service.snapshot(datetime.now(timezone.utc))
        research_items: list[ResearchItem] = []
        if self._settings.ai_research_enabled:
            topics = self._determine_research_topics(market_snapshot, portfolio_snapshot.positions)
            research_items = await self._researcher.gather(topics)
        prompt = self._build_prompt(market_snapshot, portfolio_snapshot, research_items)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Croc-Bot's autonomous trading assistant. "
                    "Respond with valid JSON matching the provided schema. "
                    "Focus on actionable insights while maintaining strict risk discipline."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        response_text = await asyncio.to_thread(
            local_chat,
            messages,
            temperature=0.1,
            max_tokens=512,
            top_p=0.9,
        )
        decision = self._parse_decision(response_text)
        await self._decision_logger.log_event(
            "ai_decision",
            {
                "raw_response": response_text,
                "parsed": decision.model_dump(mode="json"),
                "market": market_snapshot,
                "research": [item.model_dump(mode="json") for item in research_items],
            },
        )
        self._last_decision = decision
        await self._apply_decision(decision)

    def _summarize_market(self) -> list[dict[str, Any]]:
        history = self._collect_recent_ticks()
        market_summary: list[dict[str, Any]] = []
        for symbol, ticks in history.items():
            if not ticks:
                continue
            sorted_ticks = sorted(ticks, key=lambda t: t.ts)
            start_price = sorted_ticks[0].price
            end_price = sorted_ticks[-1].price
            change = 0.0
            if start_price > 0:
                change = (end_price - start_price) / start_price
            avg_volume = sum(t.volume for t in sorted_ticks) / len(sorted_ticks)
            market_summary.append(
                {
                    "symbol": symbol,
                    "last_price": end_price,
                    "start_price": start_price,
                    "return": change,
                    "avg_volume": avg_volume,
                    "samples": len(sorted_ticks),
                }
            )
        return market_summary

    def _collect_recent_ticks(self) -> dict[str, list[PriceTick]]:
        grouped: dict[str, list[PriceTick]] = defaultdict(list)
        history = self._market_engine.stream.history()
        for tick in reversed(history):
            bucket = grouped[tick.symbol]
            if len(bucket) >= self._history_window:
                continue
            bucket.append(tick)
        for symbol, ticks in grouped.items():
            ticks.reverse()
        if not grouped and self._last_ticks:
            for tick in self._last_ticks.values():
                grouped[tick.symbol].append(tick)
        return grouped

    def _determine_research_topics(self, market_snapshot: list[dict[str, Any]], positions: dict[str, Any]) -> list[str]:
        symbols = sorted({entry["symbol"] for entry in market_snapshot})
        if not symbols:
            symbols = list(self._settings.supported_crypto_pairs[:3])
        active_positions = [symbol for symbol, pos in positions.items() if abs(getattr(pos, "size", 0.0)) > 0]
        topics = list(dict.fromkeys(active_positions + symbols))
        return topics[:5]

    def _build_prompt(
        self,
        market_snapshot: list[dict[str, Any]],
        portfolio_snapshot: Any,
        research_items: list[ResearchItem],
    ) -> str:
        payload = {
            "market": market_snapshot,
            "portfolio": {
                "cash": portfolio_snapshot.cash,
                "equity": portfolio_snapshot.equity,
                "pnl_realized": portfolio_snapshot.pnl_realized,
                "pnl_unrealized": portfolio_snapshot.pnl_unrealized,
                "total_equity": portfolio_snapshot.total_equity,
                "positions": {
                    symbol: {
                        "size": pos.size,
                        "avg_price": pos.average_price,
                        "realized_pnl": pos.realized_pnl,
                    }
                    for symbol, pos in portfolio_snapshot.positions.items()
                },
            },
            "research": [item.model_dump() for item in research_items],
            "instructions": {
                "max_trades": self._max_trades,
                "history_window": self._history_window,
                "required_schema": {
                    "strategy": {
                        "target_aggression": "Optional integer 1-10",
                        "rationale": "Why the adjustment is needed",
                        "notes": "List of bullet points",
                    },
                    "trades": [
                        {
                            "symbol": "Trading pair",
                            "action": "buy|sell|flat",
                            "confidence": "0-1",
                            "size_fraction": "Optional % of equity (0-1)",
                            "reasoning": "Short explanation",
                        }
                    ],
                    "research_summary": "Concise natural language summary",
                    "risk_considerations": "List of risk notes",
                },
            },
        }
        return json.dumps(payload)

    def _parse_decision(self, response_text: str) -> AssistantDecision:
        try:
            return AssistantDecision.model_validate_json(response_text)
        except Exception as exc:  # pragma: no cover - depends on model output
            self._logger.warning("failed to parse assistant response", error=str(exc))
            return AssistantDecision()

    async def _apply_decision(self, decision: AssistantDecision) -> None:
        if decision.strategy and decision.strategy.target_aggression:
            aggression = max(1, min(10, decision.strategy.target_aggression))
            await self._state_service.set_aggression(aggression)
            self._strategy_engine.set_aggression(aggression)
            await self._decision_logger.log_event(
                "strategy_update",
                {
                    "aggression": aggression,
                    "rationale": decision.strategy.rationale,
                    "notes": decision.strategy.notes,
                },
            )
        if not self._signal_queue or not decision.trades:
            return
        submitted = 0
        for trade in decision.trades:
            if submitted >= self._max_trades:
                break
            await self._submit_trade(trade)
            submitted += 1

    async def _submit_trade(self, trade: TradeRecommendation) -> None:
        symbol = trade.symbol
        tick = self._last_ticks.get(symbol)
        if tick is None:
            return
        action = trade.action.lower()
        if action not in {"buy", "sell"}:
            return
        confidence = trade.confidence if trade.confidence is not None else 0.5
        confidence = max(0.0, min(1.0, confidence))
        signal_type = SignalType.LONG if action == "buy" else SignalType.SHORT
        strength = confidence if action == "buy" else -confidence
        signal = Signal(symbol=symbol, signal=signal_type, strength=strength, ts=datetime.now(timezone.utc))
        try:
            self._signal_queue.put_nowait(signal)
        except asyncio.QueueFull:
            self._logger.warning("signal queue full when enqueuing ai trade", symbol=symbol)
            return
        await self._decision_logger.log_event(
            "trade_signal",
            {
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
                "reasoning": trade.reasoning,
                "size_fraction": trade.size_fraction,
            },
        )


__all__ = ["AIAssistant"]
