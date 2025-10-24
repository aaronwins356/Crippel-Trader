"""SQLite persistence layer for the firm."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from ..logging import get_logger


SCHEMA = """
CREATE TABLE IF NOT EXISTS worker_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL,
    bot_type TEXT NOT NULL,
    action TEXT NOT NULL,
    ts TEXT NOT NULL,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    fees REAL NOT NULL,
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aggression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value INTEGER NOT NULL,
    ts TEXT NOT NULL
);
"""


@dataclass
class SqliteRepository:
    """Lightweight repository storing firm activity."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
        self._logger = get_logger("persistence", path=str(self.path))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_worker_event(self, bot_id: str, bot_type: str, action: str, payload: dict[str, Any] | None = None) -> None:
        ts = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO worker_events(bot_id, bot_type, action, ts, payload) VALUES (?, ?, ?, ?, ?)",
                (bot_id, bot_type, action, ts, json.dumps(payload or {})),
            )
        self._logger.info("worker_event", bot_id=bot_id, action=action)

    def record_trade(
        self,
        bot_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        fees: float,
    ) -> None:
        ts = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO trades(bot_id, symbol, side, quantity, price, fees, ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (bot_id, symbol, side, quantity, price, fees, ts),
            )
        self._logger.info("trade", bot_id=bot_id, symbol=symbol, side=side, qty=quantity)

    def record_aggression(self, value: int) -> None:
        ts = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute("INSERT INTO aggression(value, ts) VALUES (?, ?)", (value, ts))
        self._logger.info("aggression", value=value)

    def worker_history(self, bot_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT bot_type, action, ts, payload FROM worker_events WHERE bot_id=? ORDER BY id", (bot_id,)
            )
            rows = cursor.fetchall()
        return [
            {
                "bot_type": row[0],
                "action": row[1],
                "ts": row[2],
                "payload": json.loads(row[3]) if row[3] else {},
            }
            for row in rows
        ]

    def recent_trades(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT bot_id, symbol, side, quantity, price, fees, ts FROM trades ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
        return [
            {
                "bot_id": row[0],
                "symbol": row[1],
                "side": row[2],
                "quantity": row[3],
                "price": row[4],
                "fees": row[5],
                "ts": row[6],
            }
            for row in rows
        ]
