"""Worker registry tracking lifecycle and performance."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from .interfaces import BotProtocol


@dataclass
class BotRecord:
    """Track metadata for a worker bot."""

    bot: BotProtocol
    bot_type: str
    hired_at: float
    cooldown_until: float = 0.0
    last_score: float = 0.0
    last_action: str = "hired"
    meta: dict[str, float] = field(default_factory=dict)

    @property
    def tenure(self) -> float:
        return max(0.0, time.time() - self.hired_at)


class BotRegistry:
    """In-memory registry with convenience helpers."""

    def __init__(self) -> None:
        self._records: Dict[str, BotRecord] = {}

    def register(self, record: BotRecord) -> None:
        self._records[record.bot.bot_id] = record

    def unregister(self, bot_id: str) -> None:
        self._records.pop(bot_id, None)

    def get(self, bot_id: str) -> Optional[BotRecord]:
        return self._records.get(bot_id)

    def all(self) -> Iterable[BotRecord]:
        return list(self._records.values())

    def by_type(self, bot_type: str) -> list[BotRecord]:
        return [record for record in self._records.values() if record.bot_type == bot_type]

    def active_bots(self) -> list[BotRecord]:
        return list(self._records.values())

    def mark_action(self, bot_id: str, action: str) -> None:
        record = self._records.get(bot_id)
        if record:
            record.last_action = action
            record.meta[f"action_{int(time.time())}"] = 1.0

    def update_score(self, bot_id: str, score: float) -> None:
        record = self._records.get(bot_id)
        if record:
            record.last_score = score

    def apply_cooldown(self, bot_id: str, seconds: float) -> None:
        record = self._records.get(bot_id)
        if record:
            record.cooldown_until = time.time() + seconds

    def is_in_cooldown(self, bot_id: str) -> bool:
        record = self._records.get(bot_id)
        if not record:
            return False
        return time.time() < record.cooldown_until
