"""Historical replay feed for deterministic simulations."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

from ..models.types import Tick
from .feed_base import Feed


class ReplayFeed(Feed):
    """Replay ticks from a CSV/Parquet file."""

    def __init__(self, symbol: str, path: Path | None, *, speed: float = 1.0) -> None:
        super().__init__(symbol)
        self.path = path
        self.speed = speed
        self._ticks: list[Tick] = []
        self._cursor = 0

    async def connect(self) -> None:
        if self.path is None:
            self._ticks = list(self._generate_synthetic())
        else:
            self._ticks = list(self._load_ticks(self.path))
        self._cursor = 0

    async def disconnect(self) -> None:
        self._ticks.clear()
        self._cursor = 0

    def _load_ticks(self, path: Path) -> Iterable[Tick]:
        if path.suffix == ".npy":
            data = np.load(path, allow_pickle=True)
            for row in data:
                yield Tick(**row)
            return
        import pandas as pd  # imported lazily to keep startup fast

        if path.suffix in {".parquet"}:
            frame = pd.read_parquet(path)
        else:
            frame = pd.read_csv(path)
        for record in frame.to_dict("records"):
            ts = record.get("timestamp")
            if not isinstance(ts, datetime):
                ts = datetime.fromisoformat(str(ts))
            yield Tick(
                timestamp=ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc),
                symbol=record.get("symbol", self.symbol),
                bid=float(record.get("bid", record.get("last", 0.0))),
                ask=float(record.get("ask", record.get("last", 0.0))),
                last=float(record.get("last", record.get("bid", 0.0))),
                volume=float(record.get("volume", 0.0)),
            )

    def _generate_synthetic(self) -> Iterable[Tick]:
        from datetime import datetime, timedelta, timezone

        base = datetime.now(tz=timezone.utc)
        for i in range(512):
            price = 100 + np.sin(i / 10) * 2
            yield Tick(
                timestamp=base + timedelta(seconds=i),
                symbol=self.symbol,
                bid=price - 0.1,
                ask=price + 0.1,
                last=price,
                volume=1.0,
            )

    async def _sleep(self, previous: Tick, current: Tick) -> None:
        delta = (current.timestamp - previous.timestamp).total_seconds()
        if delta <= 0:
            return
        await asyncio.sleep(delta / self.speed)

    def stream(self) -> AsyncIterator[Tick]:  # type: ignore[override]
        async def iterator() -> AsyncIterator[Tick]:
            if not self._ticks:
                raise RuntimeError("Replay feed not connected or empty")
            previous = self._ticks[0]
            yield previous
            for tick in self._ticks[1:]:
                await self._sleep(previous, tick)
                previous = tick
                yield tick
        return iterator()


__all__ = ["ReplayFeed"]
