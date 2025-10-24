"""Manager bot orchestrating worker lifecycle."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

from ..bots.analyst_bot import AnalystBot, AnalystConfig
from ..bots.research_bot import ResearchBot
from ..bots.risk_bot import RiskBot, RiskConfig
from ..bots.trader_bot import TraderBot, TraderConfig
from ..engine.kraken_adapter import KrakenAdapter
from ..engine.simulator import SimulatedMarketData
from ..logging import get_logger
from ..settings import AppSettings
from .economy import FirmEconomy
from .eventbus import EventBus
from .persistence import SqliteRepository
from .policies import HiringPolicy, PolicyContext
from .registry import BotRecord, BotRegistry
from .scoring import summarize_score


class ManagerBot:
    """Coordinates worker bots, hiring, and evaluation."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.event_bus = EventBus()
        self.market_data = SimulatedMarketData()
        self.economy = FirmEconomy(settings.fees, settings.risk, settings.persistence)
        self.registry = BotRegistry()
        self.policy = HiringPolicy(settings.hiring)
        self.repository = SqliteRepository(settings.persistence.database_path)
        self._logger = get_logger("manager")
        self._narrative_path: Path = settings.hiring.narrative_path
        self._narrative_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._narrative_path.exists():
            self._narrative_path.write_text("Manager narrative log\n")
        self.mode = settings.mode.mode

    async def hire(self, role: str) -> str:
        role = role.lower()
        if role == "research":
            bot = ResearchBot(
                event_bus=self.event_bus,
                ledger=self.economy.ledger,
                persistence=self.settings.persistence,
                config=None,
            )
        elif role == "analyst":
            bot = AnalystBot(
                event_bus=self.event_bus,
                ledger=self.economy.ledger,
                market_data=self.market_data,
                config=AnalystConfig(aggression=self.settings.aggression.default),
            )
        elif role == "trader":
            bot = TraderBot(
                event_bus=self.event_bus,
                ledger=self.economy.ledger,
                portfolio=self.economy.portfolio,
                market_data=self.market_data,
                risk=self.settings.risk,
                config=TraderConfig(symbol="BTC-USD", aggression=self.settings.aggression.default, mode=self.mode),
                adapter=KrakenAdapter(),
            )
        elif role == "risk":
            bot = RiskBot(
                event_bus=self.event_bus,
                ledger=self.economy.ledger,
                portfolio=self.economy.portfolio,
                config=RiskConfig(settings=self.settings.risk),
            )
        else:
            raise ValueError(f"Unknown role {role}")
        await bot.start()
        record = BotRecord(bot=bot, bot_type=bot.bot_type, hired_at=time.time())
        self.registry.register(record)
        self.repository.record_worker_event(bot.bot_id, bot.bot_type, "hired")
        self._append_narrative(f"Hired {bot.bot_type} {bot.bot_id}")
        self._logger.info("hired", bot_type=bot.bot_type, bot_id=bot.bot_id)
        return bot.bot_id

    async def fire(self, bot_id: str, reason: str = "performance") -> None:
        record = self.registry.get(bot_id)
        if not record:
            return
        await record.bot.stop()
        self.registry.unregister(bot_id)
        self.repository.record_worker_event(bot_id, record.bot_type, "fired", {"reason": reason})
        self._append_narrative(f"Fired {record.bot_type} {bot_id} for {reason}")
        self._logger.info("fired", bot_id=bot_id, reason=reason)

    async def ensure_staffing(self) -> None:
        targets = {
            "research": 1,
            "analyst": 1,
            "trader": 1,
            "risk": 1,
        }
        for role, minimum in targets.items():
            if len(self.registry.by_type(role)) < minimum:
                await self.hire(role)

    async def evaluate_workers(self) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for record in list(self.registry.active_bots()):
            metrics = await record.bot.on_evaluate()
            for key, value in metrics.items():
                self.economy.ledger.record(record.bot.bot_id, key, float(value))
            score = summarize_score(metrics)
            scores[record.bot.bot_id] = score
            self.registry.update_score(record.bot.bot_id, score)
            if self.policy.should_fire(record, score):
                await self.fire(record.bot.bot_id, reason=f"score={score:.2f}")
        return scores

    def _coverage_gap(self) -> bool:
        return any(len(self.registry.by_type(role)) == 0 for role in ("research", "analyst", "trader", "risk"))

    async def maybe_hire(self) -> None:
        context = PolicyContext(
            conscience_score=self.economy.conscience_score(),
            coverage_gap=self._coverage_gap(),
            active_workers=len(list(self.registry.active_bots())),
            realized_pnl=self.economy.realized_pnl,
            unrealized_pnl=self.economy.unrealized_pnl,
            drawdown=self.economy.max_drawdown,
        )
        if not self.policy.should_hire(context):
            return
        for role in ("research", "analyst", "trader", "risk"):
            if len(self.registry.by_type(role)) == 0:
                await self.hire(role)
                self._append_narrative(f"Hired {role} due to coverage gap")
                break

    async def run_once(self) -> Dict[str, float]:
        await self.ensure_staffing()
        self.market_data.advance_time()
        scores = await self.evaluate_workers()
        await self.maybe_hire()
        equity = self.economy.portfolio.total_equity()
        self.economy.update_equity(equity)
        return scores

    async def shutdown(self) -> None:
        for record in list(self.registry.active_bots()):
            await self.fire(record.bot.bot_id, reason="shutdown")

    def status(self) -> dict[str, object]:
        equity = self.economy.portfolio.total_equity()
        return {
            "equity": equity,
            "realized_pnl": self.economy.realized_pnl,
            "unrealized_pnl": self.economy.unrealized_pnl,
            "drawdown": self.economy.max_drawdown,
            "conscience": self.economy.conscience_score(),
            "equity_history": [(ts.isoformat(), value) for ts, value in self.economy.equity_series()],
            "mode": self.mode,
            "aggression": self.settings.aggression.default,
            "workers": [
                {
                    "bot_id": record.bot.bot_id,
                    "type": record.bot_type,
                    "score": record.last_score,
                    "tenure": record.tenure,
                    "last_action": record.last_action,
                }
                for record in self.registry.active_bots()
            ],
        }

    def _append_narrative(self, message: str) -> None:
        entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
        with self._narrative_path.open("a") as fp:
            fp.write(entry)
