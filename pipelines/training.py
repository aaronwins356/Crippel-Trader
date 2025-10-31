"""Incremental training pipeline scaffold."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from data.ingestion import FeatureStore
from models.base import Trainable
from utils.logging import get_logger


@dataclass(slots=True)
class TrainingBatch:
    features: pd.DataFrame
    targets: np.ndarray


class OnlineTrainingPipeline:
    """Coordinates incremental updates using the latest market data."""

    def __init__(self, trainer: Trainable, store: FeatureStore, batch_size: int = 256) -> None:
        self._trainer = trainer
        self._store = store
        self._batch_size = batch_size
        self._logger = get_logger(__name__)

    def update(self, frames: Iterable[pd.DataFrame], targets: Iterable[np.ndarray]) -> None:
        buffer: list[pd.DataFrame] = []
        target_buffer: list[np.ndarray] = []

        for frame, target in zip(frames, targets):
            self._store.update(frame)
            buffer.append(self._store.latest())
            target_buffer.append(target)
            if len(buffer) >= self._batch_size:
                self._flush(buffer, target_buffer)
                buffer.clear()
                target_buffer.clear()

        if buffer:
            self._flush(buffer, target_buffer)

    def _flush(self, buffer: list[pd.DataFrame], targets: list[np.ndarray]) -> None:
        features = pd.concat(buffer)
        stacked_targets = np.concatenate(targets)
        self._logger.info("online_training_update", rows=len(features))
        self._trainer.update(features, stacked_targets)
