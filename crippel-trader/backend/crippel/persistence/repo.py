"""SQLite persistence layer."""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import aiosqlite

from ..config import get_settings
from ..models.core import Fill


class Repository:
    """Async SQLite repository."""

    def __init__(self, db_path: Path | None = None) -> None:
        settings = get_settings()
        self.db_path = db_path or Path(settings.database_url.split("///")[-1])
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        schema_sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(schema_sql)
            await conn.commit()

    async def record_fill(self, fill: Fill) -> None:
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "INSERT OR REPLACE INTO trades (id, symbol, side, size, price, fee, ts)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        fill.order_id,
                        fill.symbol,
                        fill.side.value,
                        fill.size,
                        fill.price,
                        fill.fee,
                        fill.ts.isoformat(),
                    ),
                )
                await conn.commit()

    async def record_aggression(self, aggression: int) -> None:
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "INSERT INTO aggression_changes (aggression, ts) VALUES (?, ?)",
                    (aggression, datetime.utcnow().isoformat()),
                )
                await conn.commit()
