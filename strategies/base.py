"""Strategy interfaces and factory utilities."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Mapping, Protocol

import numpy as np
import pandas as pd

from models.base import AsyncModelProtocol, ModelProtocol


class Strategy(Protocol):
    """Protocol describing a trading strategy."""

    name: str

    async def on_bar(self, data: pd.DataFrame) -> None:
        ...


@dataclass(slots=True)
class Signal:
    """Normalized trading signal with type safety."""

    timestamp: pd.Timestamp
    symbol: str
    side: str  # "buy" | "sell" | "flat"
    size: float
    confidence: float


class ModelDrivenStrategy(abc.ABC):
    """Base class coordinating model inference and signal creation."""

    def __init__(
        self,
        name: str,
        model: ModelProtocol,
        async_model: AsyncModelProtocol | None = None,
    ) -> None:
        self.name = name
        self._model = model
        self._async_model = async_model

    async def on_bar(self, data: pd.DataFrame) -> None:
        features = self.prepare_features(data)
        if self._async_model:
            outputs = await self._async_model.predict_async(features)
        else:
            outputs = self._model.predict(features)
        await self.dispatch_signals(self.interpret_outputs(outputs, data))

    @abc.abstractmethod
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform raw bars into model-ready features."""

    @abc.abstractmethod
    def interpret_outputs(self, outputs: np.ndarray, data: pd.DataFrame) -> list[Signal]:
        """Map model outputs into actionable signals."""

    @abc.abstractmethod
    async def dispatch_signals(self, signals: list[Signal]) -> None:
        """Handle generated signals (e.g. send to execution layer)."""


class StrategyFactory:
    """Registry-backed factory for dependency-injected strategies."""

    def __init__(self) -> None:
        self._registry: dict[str, type[ModelDrivenStrategy]] = {}

    def register(self, name: str, strategy_cls: type[ModelDrivenStrategy]) -> None:
        self._registry[name] = strategy_cls

    def create(self, config: Mapping[str, object], **deps: object) -> ModelDrivenStrategy:
        strategy_name = config["name"]
        if strategy_name not in self._registry:
            raise KeyError(f"Unknown strategy: {strategy_name}")
        strategy_cls = self._registry[strategy_name]
        return strategy_cls(**config.get("params", {}), **deps)
