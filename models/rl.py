"""RL integration helpers using optional third-party libraries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

import numpy as np
import pandas as pd

from .base import ModelBundle, PolicyNetwork

if TYPE_CHECKING:  # pragma: no cover - optional heavy deps
    from stable_baselines3 import PPO  # type: ignore


@dataclass(slots=True)
class RLModelBundle(ModelBundle):
    """Model bundle with policy reference for RL environments."""

    policy: PolicyNetwork | None = None


class StableBaselinesFactory:
    """Factory creating Stable Baselines models when available."""

    def create(self, config: Mapping[str, Any]) -> RLModelBundle:
        algorithm = config.get("algorithm", "ppo")
        policy_kwargs = config.get("policy_kwargs", {})
        env = config["env"]

        if algorithm.lower() != "ppo":  # pragma: no cover - example placeholder
            raise NotImplementedError(f"Unsupported algorithm: {algorithm}")

        model = self._build_ppo(env=env, policy_kwargs=policy_kwargs)
        bundle = RLModelBundle(model=model, async_model=None, trainer=None, policy=model)
        return bundle

    def _build_ppo(self, env: Any, policy_kwargs: Mapping[str, Any]) -> PolicyNetwork:
        try:
            from stable_baselines3 import PPO
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("stable-baselines3 is not installed") from exc

        return PPO("MlpPolicy", env, policy_kwargs=policy_kwargs, verbose=0)


class OnlineUpdater:
    """Simple online update routine for incremental learning."""

    def __init__(self, window: int) -> None:
        self._window = window
        self._buffer: list[tuple[pd.DataFrame, np.ndarray]] = []

    def queue(self, features: pd.DataFrame, targets: np.ndarray) -> None:
        self._buffer.append((features, targets))
        if len(self._buffer) > self._window:
            self._buffer.pop(0)

    def flush(self, trainer: Any) -> None:
        for features, targets in self._buffer:
            trainer.update(features, targets)
        self._buffer.clear()
