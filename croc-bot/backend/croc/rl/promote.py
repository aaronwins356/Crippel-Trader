"""Promotion helpers for activating trained models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..bus import EventBus
from ..storage.model_registry import ModelRegistry, ModelVersion


@dataclass
class Promoter:
    registry: ModelRegistry
    bus: Optional[EventBus] = None

    async def promote(self, version: str) -> ModelVersion:
        metadata = self.registry.activate(version)
        await self._emit("model.promoted", {"version": metadata.version, "code_sha": metadata.code_sha})
        return metadata

    async def rollback(self, version: Optional[str] = None) -> ModelVersion:
        metadata = self.registry.rollback(version)
        await self._emit("model.rollback", {"version": metadata.version})
        return metadata

    async def _emit(self, topic: str, payload: dict) -> None:
        if not self.bus:
            return
        await self.bus.publish(topic, payload)


__all__ = ["Promoter"]
