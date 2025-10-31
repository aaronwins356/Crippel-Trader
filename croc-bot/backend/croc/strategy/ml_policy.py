"""Strategy that runs a learned policy with strict latency budget."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Mapping, Optional

import numpy as np

from ..config import StrategyConfig
from ..models.types import Order, OrderType, Position, Side, Tick
from ..storage.model_registry import ModelRegistry
from .base import BaseStrategy

try:  # pragma: no cover - heavy optional imports
    import torch
except ModuleNotFoundError:  # pragma: no cover
    torch = None

try:  # pragma: no cover
    import onnxruntime as ort
except ModuleNotFoundError:  # pragma: no cover
    ort = None


class MLPolicyStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig, registry: ModelRegistry) -> None:
        super().__init__(config)
        self.registry = registry
        params = config.params
        self.timeout = float(params.get("timeout_ms", 10)) / 1000
        self.order_size = float(params.get("order_size", 0.01))
        self.threshold = float(params.get("threshold", 0.1))
        self._model_path: Optional[Path] = None
        self._torch_module = None
        self._onnx_session = None

    async def warmup(self, history: list[Tick]) -> None:
        active = self.registry.active_model()
        if active:
            self.reload(active)

    def reload(self, path: Path) -> None:
        if path == self._model_path:
            return
        suffix = path.suffix.lower()
        if suffix == ".pt":
            if torch is None:
                raise RuntimeError("torch not installed")
            try:
                module = torch.jit.load(str(path))  # type: ignore[union-attr]
            except RuntimeError:
                module = torch.load(str(path))  # type: ignore[union-attr]
            if hasattr(module, "eval"):
                module = module.eval()
            self._torch_module = module
            self._onnx_session = None
        elif suffix == ".onnx":
            if ort is None:
                raise RuntimeError("onnxruntime not installed")
            self._onnx_session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            self._torch_module = None
        else:
            raise ValueError(f"Unsupported model format: {suffix}")
        self._model_path = path

    async def on_tick(self, tick: Tick, features: np.ndarray, position: Position) -> Optional[Order]:
        if self._model_path is None:
            return None
        try:
            action = await asyncio.wait_for(
                asyncio.to_thread(self._predict_sync, features.astype(np.float32)),
                timeout=self.timeout,
            )
        except (asyncio.TimeoutError, RuntimeError):
            return None
        action = float(np.tanh(action))
        if action > self.threshold and position.size <= 0:
            return self.new_order(
                symbol=tick.symbol,
                side=Side.BUY,
                size=self.order_size * abs(action),
                price=tick.ask,
                order_type=OrderType.MARKET,
            )
        if action < -self.threshold and position.size >= 0:
            return self.new_order(
                symbol=tick.symbol,
                side=Side.SELL,
                size=self.order_size * abs(action),
                price=tick.bid,
                order_type=OrderType.MARKET,
            )
        return None

    def configure(self, params: Mapping[str, float]) -> None:
        super().configure(params)
        if "order_size" in params:
            self.order_size = float(params["order_size"])
        if "threshold" in params:
            self.threshold = float(params["threshold"])

    def _predict_sync(self, features: np.ndarray) -> float:
        if self._torch_module is not None:
            with torch.no_grad():  # type: ignore[union-attr]
                tensor = torch.from_numpy(features).unsqueeze(0)  # type: ignore[attr-defined]
                out = self._torch_module(tensor)  # type: ignore[operator]
                return float(out.squeeze().cpu().numpy())
        if self._onnx_session is not None:
            input_name = self._onnx_session.get_inputs()[0].name
            result = self._onnx_session.run(None, {input_name: features[None, :]})
            return float(result[0].squeeze())
        raise RuntimeError("No policy loaded")


__all__ = ["MLPolicyStrategy"]
