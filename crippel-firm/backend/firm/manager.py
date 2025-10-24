"""ManagerBot orchestrating worker lifecycle."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Dict, Optional, Type

from .bots.analyst_bot import AnalystBot, AnalystConfig
from .bots.research_bot import ResearchBot, ResearchConfig
from .bots.risk_bot import RiskBot, RiskConfig
from .bots.trader_bot import TraderBot, TraderConfig
from .config import FirmConfig
from .economy import FirmEconomy
from .engine.evaluation import aggregate_scores, score_bot
from .engine.kraken_adapter import KrakenAdapter
from .engine.simulator import SimulatedMarketData
from .eventbus import EventBus
from .interfaces import BotProtocol
from .registry import BotRecord, BotRegistry
from .utils.logging import get_logger


class ManagerBot:
    """Coordinates all firm activities."""

    def __init__(self, config: FirmConfig) -> None:
        self.config = config
        self.logger = get_logger("manager")
        self.event_bus = EventBus()
        self.market_data = SimulatedMarketData()
        self.kraken = KrakenAdapter()
        state_path = Path(self.config.manager.persistence_path)
        self.economy = FirmEconomy(self.config.capital, state_path)
        self.economy.load()
        self.registry = BotRegistry()
        self.performance_ledger = self.economy.ledger
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._narrative_path = Path(self.config.manager.narrative_path)
        self._loop_running = False

    async def hire_research_bot(self) -> str:
        bot = ResearchBot(
            event_bus=self.event_bus,
            performance_ledger=self.performance_ledger,
            config=ResearchConfig(settings=self.config.research),
        )
        await self._start_bot(bot)
        return bot.bot_id

    async def hire_analyst_bot(self) -> str:
        bot = AnalystBot(
            event_bus=self.event_bus,
            performance_ledger=self.performance_ledger,
            market_data=self.market_data,
        )
        await self._start_bot(bot)
        return bot.bot_id

    async def hire_trader_bot(self) -> str:
        bot = TraderBot(
            event_bus=self.event_bus,
            performance_ledger=self.performance_ledger,
            portfolio=self.economy.portfolio,
            adapter=self.kraken,
            market_data=self.market_data,
            config=TraderConfig(),
        )
        await self._start_bot(bot)
        return bot.bot_id

    async def hire_risk_bot(self) -> str:
        bot = RiskBot(
            event_bus=self.event_bus,
            performance_ledger=self.performance_ledger,
            portfolio=self.economy.portfolio,
            config=RiskConfig(capital_policy=self.config.capital),
        )
        await self._start_bot(bot)
        return bot.bot_id

    async def fire(self, bot_id: str) -> None:
        record = self.registry.get(bot_id)
        if not record:
            return
        await record.bot.stop()
        self.registry.unregister(bot_id)
        self._append_narrative(f"Fired {bot_id} ({record.bot_type})")

    async def _start_bot(self, bot: BotProtocol) -> None:
        await bot.start()
        record = BotRecord(bot=bot, bot_type=bot.bot_type, hired_at=time.time())
        self.registry.register(record)
        self._append_narrative(f"Hired {bot.bot_id} ({bot.bot_type})")

    def _append_narrative(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self._narrative_path.write_text(
            self._narrative_path.read_text() + f"\n{timestamp} - {message}" if self._narrative_path.exists() else f"{timestamp} - {message}"
        )

    async def evaluate_workers(self) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for record in list(self.registry.active_bots()):
            metrics = await record.bot.on_evaluate()
            for key, value in metrics.items():
                self.performance_ledger.record_event(record.bot.bot_id, key, float(value))
            score = score_bot(metrics)
            record.last_score = score
            scores[record.bot.bot_id] = score
            inactivity = time.time() - record.bot.last_active
            if score < self.config.hiring.fire_threshold or inactivity > self.config.hiring.inactivity_limit:
                self.logger.info("Firing bot %s due to performance=%s inactivity=%s", record.bot.bot_id, score, inactivity)
                await self.fire(record.bot.bot_id)
        return scores

    async def rebalance(self) -> None:
        equity = self.economy.portfolio.cash + self.economy.portfolio.current_exposure() + self.economy.portfolio.realized_pnl
        self.economy.update_equity(equity)
        self.economy.serialize()

    async def ensure_staffing(self) -> None:
        if len(self.registry.by_type("research")) < self.config.hiring.max_researchers:
            await self.hire_research_bot()
        if len(self.registry.by_type("analyst")) < self.config.hiring.max_analysts:
            await self.hire_analyst_bot()
        if len(self.registry.by_type("trader")) < self.config.hiring.max_traders:
            await self.hire_trader_bot()
        if len(self.registry.by_type("risk")) < self.config.hiring.max_risk_bots:
            await self.hire_risk_bot()

    async def run_once(self) -> Dict[str, float]:
        await self.ensure_staffing()
        self.market_data.advance_time()
        scores = await self.evaluate_workers()
        await self.rebalance()
        return scores

    async def shutdown(self) -> None:
        for record in list(self.registry.active_bots()):
            await self.fire(record.bot.bot_id)


