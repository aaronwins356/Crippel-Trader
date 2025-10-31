"""Model interfaces and adapters for ML/RL components."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol

import numpy as np
import pandas as pd


class ModelProtocol(Protocol):
    """Synchronous prediction interface."""

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Return model outputs given the latest features."""


class AsyncModelProtocol(Protocol):
    """Asynchronous prediction interface for latency-sensitive flows."""

    async def predict_async(self, features: pd.DataFrame) -> np.ndarray:
        """Return model outputs in an async context."""


class Trainable(Protocol):
    """Protocol for online/offline learning workflows."""

    def fit(self, features: pd.DataFrame, targets: np.ndarray) -> None:
        ...

    def update(self, features: pd.DataFrame, targets: np.ndarray) -> None:
        ...


class PolicyNetwork(Protocol):
    """Minimal interface expected from RL policy implementations."""

    def act(self, state: np.ndarray, deterministic: bool = True) -> int:
        ...

    def save(self, path: str) -> None:
        ...


@dataclass(slots=True)
class ModelBundle:
    """Container bundling sync/async model variants."""

    model: ModelProtocol
    async_model: AsyncModelProtocol | None = None
    trainer: Trainable | None = None

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        return self.model.predict(features)


class InferenceAdapter(AsyncModelProtocol):
    """Adapter wrapping synchronous models for async pipelines."""

    def __init__(self, model: ModelProtocol, *, loop=None) -> None:
        self._model = model
        self._loop = loop

    async def predict_async(self, features: pd.DataFrame) -> np.ndarray:
        loop = self._loop
        if loop is None:
            import asyncio

            loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._model.predict, features)


class ConfigurableModelFactory(abc.ABC):
    """Factory for constructing models from config dictionaries."""

    @abc.abstractmethod
    def create(self, config: Mapping[str, Any]) -> ModelBundle:
        """Instantiate a model bundle based on configuration."""


def ensure_iterable(sequence: Iterable[Any] | Any) -> Iterable[Any]:
    """Normalize config values into iterables for downstream loops."""

    if isinstance(sequence, Iterable) and not isinstance(sequence, (str, bytes, bytearray)):
        return sequence
    return (sequence,)
