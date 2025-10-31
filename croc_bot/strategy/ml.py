"""Machine-learning powered strategy scaffolding."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from ..domain import MarketData, TradeAction, TradeSignal
from ..execution.base import PortfolioState
from .base import BaseStrategy, StrategyConfig


class InferenceModel(Protocol):
    """Protocol describing a synchronous inference surface."""

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Return model outputs for the provided feature vector."""


@dataclass(slots=True)
class MLStrategyConfig(StrategyConfig):
    """Configuration for ML strategies."""

    model_path: Path
    feature_dim: int
    action_mapping: dict[str, str]


def _load_model(path: Path) -> InferenceModel:
    raise NotImplementedError(
        "Model loading is delegated to the application and should be provided "
        "via dependency injection."
    )


class MLStrategy(BaseStrategy):
    """Thin wrapper that delegates inference to an injected model."""

    def __init__(
        self,
        config: MLStrategyConfig,
        model: InferenceModel | None = None,
        feature_fn: Callable[[MarketData, PortfolioState], np.ndarray] | None = None,
    ) -> None:
        super().__init__(config)
        self._config = config
        self._model = model or _load_model(config.model_path)
        self._feature_fn = feature_fn or self._default_features

    def on_market_data(self, market: MarketData, portfolio: PortfolioState) -> TradeAction:
        features = self._feature_fn(market, portfolio)
        outputs = self._model.predict(features)
        signal = self._interpret_output(outputs)
        return TradeAction(signal=signal)

    def _default_features(self, market: MarketData, portfolio: PortfolioState) -> np.ndarray:
        return np.array([
            market.price,
            portfolio.cash,
            portfolio.equity,
            portfolio.position_units,
        ], dtype=float)

    def _interpret_output(self, outputs: np.ndarray) -> TradeSignal:
        if outputs.ndim == 0:
            return TradeSignal.BUY if float(outputs) > 0 else TradeSignal.SELL
        if outputs.ndim == 1 and outputs.size >= 3:
            idx = int(np.argmax(outputs))
            mapping = list(self._config.action_mapping.values())
            if idx < len(mapping):
                label = mapping[idx].upper()
                return TradeSignal[label]
        raise ValueError("Unable to interpret model outputs")
