"""AI self-reconfiguration control loop for simulation mode."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import numpy as np

from ..bus import EventBus
from ..config import Settings
from ..runtime.metrics import MetricsCollector
from ..strategy.base import BaseStrategy


class AISimulationController:
    """Adapts strategy parameters based on simulated performance."""

    def __init__(
        self,
        *,
        settings: Settings,
        metrics: MetricsCollector,
        strategy: BaseStrategy,
        bus: EventBus,
    ) -> None:
        self.settings = settings
        self.metrics = metrics
        self.strategy = strategy
        self.bus = bus
        self._rng = np.random.default_rng(settings.simulation.seed)
        self._logger = logging.getLogger("croc.simulation")
        self._attach_file_logger(Path("logs/ai_simulation.log"))
        self._last_update: Dict[str, float] | None = None

    def _attach_file_logger(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        for handler in self._logger.handlers:
            if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == path:
                break
        else:
            handler = logging.FileHandler(path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = True

    async def reconfigure(self) -> None:
        snapshot = await self.metrics.snapshot()
        sim_cfg = self.settings.simulation
        params = self.settings.strategy.params
        current_threshold = float(params.get("threshold", 0.0))
        current_order = float(params.get("order_size", sim_cfg.min_order_size))

        volatility_pressure = 1.0 + min(0.5, abs(snapshot.exposure) * 0.05)
        drawdown_pressure = 1.0 - min(0.5, snapshot.drawdown / 1_000 if snapshot.drawdown else 0.0)
        pnl_pressure = 1.0 + np.tanh(snapshot.pnl / 1_000) * 0.1

        threshold_noise = float(self._rng.normal(0.0, sim_cfg.threshold_jitter))
        new_threshold = np.clip(
            current_threshold * volatility_pressure + threshold_noise,
            0.0,
            sim_cfg.max_threshold,
        )

        order_noise = float(self._rng.normal(0.0, sim_cfg.order_size_jitter))
        base_order = current_order * drawdown_pressure * pnl_pressure + order_noise
        new_order = float(
            np.clip(base_order, sim_cfg.min_order_size, sim_cfg.max_order_size)
        )

        update: Dict[str, float] = {}
        if not np.isclose(new_threshold, current_threshold):
            update["threshold"] = float(np.round(new_threshold, 6))
        if not np.isclose(new_order, current_order):
            update["order_size"] = float(np.round(new_order, 6))

        if not update or update == self._last_update:
            return

        self.settings.strategy.params.update(update)
        self.strategy.configure(update)
        self._last_update = update

        log_message = (
            "simulation_reconfigure threshold=%0.4f order_size=%0.4f pnl=%0.2f drawdown=%0.2f"
            % (
                update.get("threshold", current_threshold),
                update.get("order_size", current_order),
                snapshot.pnl,
                snapshot.drawdown,
            )
        )
        self._logger.info(log_message)
        await self.bus.publish(
            "ai",
            {
                "event": "simulation_reconfigure",
                "params": update,
                "pnl": snapshot.pnl,
                "drawdown": snapshot.drawdown,
                "exposure": snapshot.exposure,
            },
        )


__all__ = ["AISimulationController"]
