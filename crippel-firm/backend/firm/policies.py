"""Hiring and firing policies for the manager."""
from __future__ import annotations

import time
from dataclasses import dataclass

from ..settings import HiringSettings
from .registry import BotRecord


@dataclass
class PolicyContext:
    """Snapshot of firm state used to make policy decisions."""

    conscience_score: float
    coverage_gap: bool
    active_workers: int
    realized_pnl: float
    unrealized_pnl: float
    drawdown: float


@dataclass
class HiringPolicy:
    """Evaluate hire/fire decisions using thresholds and cooldowns."""

    settings: HiringSettings

    def should_hire(self, context: PolicyContext) -> bool:
        if not context.coverage_gap:
            return False
        return context.conscience_score >= self.settings.hire_threshold

    def should_fire(self, record: BotRecord, score: float) -> bool:
        if record.tenure < self.settings.min_tenure_sec:
            return False
        if time.time() < record.cooldown_until:
            return False
        return score <= self.settings.fire_threshold

    def cooldown(self) -> float:
        return self.settings.cooldown_sec
