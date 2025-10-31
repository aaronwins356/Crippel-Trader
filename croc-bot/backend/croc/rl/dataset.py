"""Dataset builders for offline RL experience tuples."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import json
import numpy as np

from ..config import StorageConfig
from ..data.features import FeaturePipeline, features_from_ticks
from ..models.types import Tick


@dataclass(frozen=True)
class Experience:
    """Single transition collected from live trading."""

    state: np.ndarray
    action: np.ndarray
    reward: float
    next_state: np.ndarray
    done: bool
    timestamp: datetime


class ExperienceDataset:
    """In-memory dataset wrapping numpy arrays for efficient sampling."""

    def __init__(self, experiences: Sequence[Experience]) -> None:
        self._experiences = list(experiences)
        if not self._experiences:
            raise ValueError("experience dataset cannot be empty")
        self.states = np.stack([exp.state for exp in self._experiences])
        self.actions = np.stack([exp.action for exp in self._experiences])
        self.rewards = np.array([exp.reward for exp in self._experiences], dtype=float)
        self.next_states = np.stack([exp.next_state for exp in self._experiences])
        self.dones = np.array([exp.done for exp in self._experiences], dtype=bool)
        self.timestamps = [exp.timestamp for exp in self._experiences]

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._experiences)

    def __iter__(self) -> Iterator[Experience]:
        return iter(self._experiences)


def _load_tick_history(storage: StorageConfig, symbol: str) -> list[Tick]:
    """Load tick history for feature reconstruction."""

    path = storage.ticks / f"{symbol.replace('/', '_')}.csv"
    if not path.exists():
        return []
    rows = path.read_text().strip().splitlines()
    if len(rows) <= 1:
        return []
    ticks: list[Tick] = []
    for row in rows[1:]:
        timestamp, bid, ask, last, volume = row.split(",")
        ticks.append(
            Tick(
                timestamp=datetime.fromisoformat(timestamp),
                symbol=symbol,
                bid=float(bid),
                ask=float(ask),
                last=float(last),
                volume=float(volume),
            )
        )
    return ticks


def _load_experience_files(directory: Path, since: datetime | None, until: datetime | None) -> Iterable[dict]:
    if not directory.exists():
        return []
    entries: list[dict] = []
    for path in sorted(directory.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            payload = json.loads(line)
            ts = datetime.fromisoformat(payload["timestamp"]) if "timestamp" in payload else None
            if since and ts and ts < since:
                continue
            if until and ts and ts > until:
                continue
            entries.append(payload)
    return entries


def _build_experience(payload: dict, features: np.ndarray) -> Experience:
    idx = payload.get("feature_index", -1)
    if idx < 0 or idx >= len(features):
        raise ValueError("invalid feature index in payload")
    state = features[idx - 1] if idx > 0 else features[idx]
    next_state = features[min(idx, len(features) - 1)]
    return Experience(
        state=state.astype(np.float32),
        action=np.asarray(payload.get("action", [0.0]), dtype=np.float32),
        reward=float(payload.get("reward", 0.0)),
        next_state=next_state.astype(np.float32),
        done=bool(payload.get("done", False)),
        timestamp=datetime.fromisoformat(payload["timestamp"]),
    )


def build_datasets(
    storage: StorageConfig,
    *,
    symbol: str,
    since: datetime | None = None,
    until: datetime | None = None,
    eval_ratio: float = 0.2,
    pipeline: FeaturePipeline | None = None,
) -> tuple[ExperienceDataset, ExperienceDataset]:
    """Build train/eval datasets from stored experience tuples."""

    pipeline = pipeline or FeaturePipeline()
    experience_dir = Path(storage.base_dir) / "experience"
    payloads = list(_load_experience_files(experience_dir, since, until))
    if not payloads:
        raise FileNotFoundError("no experience payloads found for requested window")

    ticks = _load_tick_history(storage, symbol)
    if not ticks:
        raise FileNotFoundError("tick history unavailable; cannot build features")
    features = features_from_ticks(ticks, pipeline)

    experiences = [_build_experience(payload, features) for payload in payloads]
    split = max(1, int(len(experiences) * (1 - eval_ratio)))
    train_experiences = experiences[:split]
    eval_experiences = experiences[split:]
    if not eval_experiences:
        eval_experiences = train_experiences[-1:]
    train = ExperienceDataset(train_experiences)
    eval_set = ExperienceDataset(eval_experiences)
    return train, eval_set


__all__ = ["Experience", "ExperienceDataset", "build_datasets"]
