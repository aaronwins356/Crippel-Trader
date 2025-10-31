"""Configuration models using Pydantic for validation."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, validator


class DataConfig(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["BTC-USD"])
    bar_interval: str = "1m"


class ModelConfig(BaseModel):
    name: str = "baseline"
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyConfig(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class ExecutionConfig(BaseModel):
    venue: str = "paper"
    max_concurrency: int = 10

    @validator("max_concurrency")
    def validate_concurrency(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_concurrency must be positive")
        return value


class AppConfig(BaseModel):
    data: DataConfig = Field(default_factory=DataConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    strategy: StrategyConfig
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "AppConfig":
        return cls(**values)
