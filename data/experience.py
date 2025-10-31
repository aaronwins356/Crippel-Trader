"""Experience logging utilities for reinforcement learning workflows."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Protocol

import pandas as pd


def _ensure_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


@dataclass(slots=True)
class TradeExperience:
    """Container capturing a single state-action-reward tuple."""

    timestamp: datetime
    symbol: str
    state: Mapping[str, float]
    action: str
    reward: float
    done: bool
    info: MutableMapping[str, float | int | str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["state"] = dict(self.state)
        payload["info"] = dict(self.info)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "TradeExperience":
        return cls(
            timestamp=_ensure_datetime(payload["timestamp"]),
            symbol=str(payload["symbol"]),
            state=dict(payload.get("state", {})),
            action=str(payload["action"]),
            reward=float(payload["reward"]),
            done=bool(payload.get("done", False)),
            info=dict(payload.get("info", {})),
        )


class ExperienceRepository(Protocol):
    """Persistence interface for experience tuples."""

    def append(self, experiences: Iterable[TradeExperience]) -> None:
        ...

    def load(self, limit: int | None = None) -> pd.DataFrame:
        ...


class FileExperienceRepository:
    """JSONL-backed implementation compatible with append-only writes."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, experiences: Iterable[TradeExperience]) -> None:
        if not experiences:
            return
        with self._path.open("a", encoding="utf-8") as handle:
            for experience in experiences:
                handle.write(json.dumps(experience.to_dict()))
                handle.write("\n")

    def load(self, limit: int | None = None) -> pd.DataFrame:
        if not self._path.exists():
            return pd.DataFrame()

        records: list[dict[str, object]] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                records.append(json.loads(line))

        if not records:
            return pd.DataFrame()

        if limit is not None:
            records = records[-limit:]

        frame = pd.DataFrame.from_records(records)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        return frame

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()


__all__ = [
    "TradeExperience",
    "ExperienceRepository",
    "FileExperienceRepository",
]

