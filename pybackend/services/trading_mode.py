"""Trading mode coordination between paper and live engines."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List

from ..utils.logger import get_child

logger = get_child("mode")

EventHandler = Callable[[Any], Any]


class TradingModeService:
    def __init__(self, market_data_service, live_trading_service, default_mode: str = "paper") -> None:
        self.market_data_service = market_data_service
        self.live_trading_service = live_trading_service
        self.available_modes = ["paper", "live"]
        self.current_mode = default_mode if default_mode in self.available_modes else "paper"
        self._listeners: Dict[str, List[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> None:
        self._listeners[event].append(handler)

    def off(self, event: str, handler: EventHandler) -> None:
        if handler in self._listeners.get(event, []):
            self._listeners[event].remove(handler)

    def _emit(self, event: str, payload: Any) -> None:
        for handler in list(self._listeners.get(event, [])):
            try:
                result = handler(payload)
                if hasattr(result, "__await__"):
                    import asyncio

                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)
                    except RuntimeError:
                        asyncio.run(result)  # pragma: no cover - convenience
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Mode handler failure", exc_info=exc)

    def get_mode(self) -> str:
        return self.current_mode

    def get_available_modes(self) -> List[str]:
        return list(self.available_modes)

    def is_paper_mode(self) -> bool:
        return self.current_mode == "paper"

    def is_live_mode(self) -> bool:
        return self.current_mode == "live"

    def set_mode(self, mode: str) -> str:
        if mode not in self.available_modes:
            raise ValueError(f"Unknown mode: {mode}")
        if mode == self.current_mode:
            return self.current_mode
        self.current_mode = mode
        event = {"type": "mode:change", "mode": mode}
        self._emit("mode:change", event)
        return self.current_mode

    def get_paper_service(self):
        return self.market_data_service

    def get_live_service(self):
        return self.live_trading_service


__all__ = ["TradingModeService"]
