"""Lightweight dependency injection container."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ServiceContainer:
    """Explicit registry for application services."""

    def __init__(self) -> None:
        self._providers: dict[str, Callable[["ServiceContainer"], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register(self, name: str, provider: Callable[["ServiceContainer"], Any]) -> None:
        self._providers[name] = provider

    def resolve(self, name: str) -> Any:
        if name not in self._instances:
            if name not in self._providers:
                raise KeyError(f"Unknown service: {name}")
            self._instances[name] = self._providers[name](self)
        return self._instances[name]

    def clear(self) -> None:
        self._instances.clear()
