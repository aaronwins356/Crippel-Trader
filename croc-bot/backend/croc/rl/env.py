"""Gymnasium-compatible trading environment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

try:  # pragma: no cover - fallback for slim test envs
    import gymnasium as gym
except ModuleNotFoundError:  # pragma: no cover
    import types

    class _Box:
        def __init__(self, low, high, shape, dtype):
            self.low = low
            self.high = high
            self.shape = shape
            self.dtype = dtype

    class _Env:
        metadata = {}

        def reset(self, *, seed=None, options=None):
            return None, {}

        def step(self, action):
            raise NotImplementedError

    gym = types.SimpleNamespace(Env=_Env, spaces=types.SimpleNamespace(Box=_Box))
import numpy as np

from ..data.features import FeaturePipeline, features_from_ticks
from ..models.types import Tick


@dataclass
class EnvConfig:
    max_position: float = 1.0
    transaction_cost: float = 0.0005
    drawdown_penalty: float = 0.1


class TradingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        ticks: Optional[list[Tick]] = None,
        pipeline: Optional[FeaturePipeline] = None,
        config: EnvConfig | None = None,
    ) -> None:
        super().__init__()
        self.pipeline = pipeline or FeaturePipeline()
        self.config = config or EnvConfig()
        self._ticks = ticks or self._generate_synthetic_data()
        self._features = features_from_ticks(self._ticks, self.pipeline)
        self._step_index = 0
        self._position = 0.0
        self._cash = 0.0
        self._peak_equity = 0.0
        self.action_space = gym.spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(4,), dtype=np.float32)

    def _generate_synthetic_data(self) -> list[Tick]:
        from datetime import datetime, timedelta, timezone

        ticks: list[Tick] = []
        base = datetime.now(tz=timezone.utc)
        prices = np.linspace(100, 105, 512)
        for i, price in enumerate(prices):
            ticks.append(
                Tick(
                    timestamp=base + timedelta(minutes=i),
                    symbol="SIM/USD",
                    bid=price - 0.1,
                    ask=price + 0.1,
                    last=price,
                    volume=1.0,
                )
            )
        return ticks

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict[str, Any]] = None):
        super().reset(seed=seed)
        self._step_index = self.pipeline.slow_window
        self._position = 0.0
        self._cash = 0.0
        self._peak_equity = 0.0
        self._prev_equity = 0.0
        observation = self._features[self._step_index].astype(np.float32)
        return observation, {}

    def step(self, action: np.ndarray):
        action_value = float(np.clip(action[0], -1.0, 1.0))
        target_position = action_value * self.config.max_position
        trade_size = target_position - self._position
        price = self._ticks[self._step_index].last
        self._position += trade_size
        self._cash -= trade_size * price
        transaction_cost = abs(trade_size) * price * self.config.transaction_cost
        self._cash -= transaction_cost
        self._step_index += 1
        done = self._step_index >= len(self._features) - 1
        next_price = self._ticks[self._step_index].last
        unrealised = self._position * next_price
        equity = self._cash + unrealised
        self._peak_equity = max(self._peak_equity, equity)
        drawdown = max(0.0, self._peak_equity - equity)
        pnl_delta = equity - self._prev_equity
        self._prev_equity = equity
        reward = pnl_delta - transaction_cost - self.config.drawdown_penalty * drawdown
        observation = self._features[self._step_index].astype(np.float32)
        info = {"pnl": equity, "drawdown": drawdown}
        return observation, reward, done, False, info

    def render(self) -> None:
        return None


__all__ = ["TradingEnv", "EnvConfig"]
