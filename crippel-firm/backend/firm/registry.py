"""Bot registry and metadata management."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from .interfaces import BotProtocol


@dataclass
class BotRecord:
    bot: BotProtocol
    bot_type: str
    hired_at: float
    last_score: float = 0.0


class BotRegistry:
    """Registry tracking active worker bots."""

    def __init__(self) -> None:
        self._records: Dict[str, BotRecord] = {}

    def register(self, record: BotRecord) -> None:
        self._records[record.bot.bot_id] = record

    def unregister(self, bot_id: str) -> None:
        self._records.pop(bot_id, None)

    def get(self, bot_id: str) -> Optional[BotRecord]:
        return self._records.get(bot_id)

    def active_bots(self) -> Iterable[BotRecord]:
        return list(self._records.values())

    def by_type(self, bot_type: str) -> list[BotRecord]:
        return [record for record in self._records.values() if record.bot_type == bot_type]
