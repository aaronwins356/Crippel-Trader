"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import json

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, validator

from utils.validation import (
    ValidationError,
    collect_errors,
    validate_bounds,
    validate_fee,
    validate_pairs,
    validate_positive,
)


class TradingConfig(BaseModel):
    mode: str = Field(regex="^(paper|live)$")
    capital: float
    aggression: float
    pairs: list[str]
    max_position_pct: float
    max_daily_loss_pct: float

    @validator("capital")
    def check_capital(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Capital must be positive.")
        return value

    @validator("aggression")
    def check_aggression(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError("Aggression must be between 0 and 1.")
        return value


class APIConfig(BaseModel):
    kraken_key: str
    kraken_secret: str
    discord_webhook: str


class LLMConfig(BaseModel):
    endpoint: str = Field(default="http://127.0.0.1:1234/v1/chat/completions")
    model: str
    temperature: float = 0.2
    max_tokens: int = 1024

    @validator("temperature")
    def check_temperature(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("Temperature must be between 0 and 1.")
        return value

    @validator("max_tokens")
    def check_tokens(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_tokens must be positive")
        return value


class FeesConfig(BaseModel):
    maker: float
    taker: float


class RuntimeConfig(BaseModel):
    cache_dir: str
    log_level: str = Field(default="INFO")
    refresh_interval: float = Field(default=2.0)
    read_only: bool = Field(default=True)
    log_retention: int = Field(default=7)

    @validator("refresh_interval")
    def check_refresh_interval(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("refresh_interval must be positive")
        return value

    @validator("log_retention")
    def check_retention(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("log_retention must be positive")
        return value


class AppConfig(BaseModel):
    trading: TradingConfig
    api: APIConfig
    llm: LLMConfig
    fees: FeesConfig
    runtime: RuntimeConfig


@dataclass
class ConfigResult:
    config: AppConfig | None
    errors: list[ValidationError]


def load_config(path: Path) -> ConfigResult:
    raw: Dict[str, Any]
    try:
        raw = json.loads(path.read_text())
    except FileNotFoundError:
        return ConfigResult(config=None, errors=[ValidationError("config", "config.json not found")])
    except json.JSONDecodeError as exc:
        return ConfigResult(config=None, errors=[ValidationError("config", f"Invalid JSON: {exc}")])

    try:
        config = AppConfig.parse_obj(raw)
    except PydanticValidationError as exc:
        errors = [ValidationError("/".join(map(str, err['loc'])), err['msg']) for err in exc.errors()]
        return ConfigResult(config=None, errors=errors)

    errors = collect_errors(
        validate_pairs(config.trading.pairs),
        validate_positive(config.trading.capital, "trading.capital"),
        validate_bounds(config.trading.aggression, "trading.aggression", 0.0, 1.0),
        validate_bounds(config.trading.max_position_pct, "trading.max_position_pct", 0.0, 1.0),
        validate_bounds(config.trading.max_daily_loss_pct, "trading.max_daily_loss_pct", 0.0, 1.0),
        validate_fee(config.fees.maker, "fees.maker"),
        validate_fee(config.fees.taker, "fees.taker"),
    )

    if errors:
        return ConfigResult(config=None, errors=errors)

    return ConfigResult(config=config, errors=[])


def redact_config(config: AppConfig) -> Dict[str, Any]:
    data = json.loads(config.json())
    data["api"]["kraken_key"] = "***"
    data["api"]["kraken_secret"] = "***"
    if data["api"].get("discord_webhook"):
        data["api"]["discord_webhook"] = "***"
    return data
