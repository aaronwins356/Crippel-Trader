"""Configuration loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError as PydanticValidationError,
    field_validator,
    model_validator,
)

from utils.validation import (
    ValidationError,
    collect_errors,
    validate_fee,
    validate_positive,
    validate_symbols,
)


class TradingConfig(BaseModel):
    """Trading configuration extracted from config.json."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["paper", "live"] = Field(pattern="^(paper|live)$")
    initial_capital: float = Field(gt=0)
    aggression: int = Field(ge=1, le=10)
    symbols: list[str] = Field(min_length=1)

    @field_validator("symbols")
    @classmethod
    def _strip_symbols(cls, value: list[str]) -> list[str]:
        return [symbol.strip() for symbol in value if symbol and symbol.strip()]


class APIConfig(BaseModel):
    """API credential configuration."""

    model_config = ConfigDict(extra="allow")

    kraken_key: str
    kraken_secret: str
    discord_webhook: str = ""


class LLMConfig(BaseModel):
    """LLM connection configuration."""

    model_config = ConfigDict(extra="forbid")

    endpoint: str = Field(default="http://127.0.0.1:1234")
    model: str
    temperature: float = Field(default=0.2)

    @field_validator("temperature")
    @classmethod
    def _validate_temperature(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Temperature must be between 0 and 1.")
        return value


class FeesConfig(BaseModel):
    """Exchange fee configuration."""

    model_config = ConfigDict(extra="forbid")

    maker: float
    taker: float


class RuntimeConfig(BaseModel):
    """Runtime tuning parameters."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    log_level: str = Field(default="INFO")
    read_only_mode: bool = Field(default=True)
    refresh_interval: float = Field(default=2.0)
    log_retention: int = Field(default=7)

    @model_validator(mode="before")
    @classmethod
    def _migrate_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(values) if isinstance(values, dict) else values
        if isinstance(data, dict):
            if "read_only" in data and "read_only_mode" not in data:
                data["read_only_mode"] = data.pop("read_only")
            data.setdefault("refresh_interval", 2.0)
            data.setdefault("log_retention", 7)
        return data

    @field_validator("refresh_interval")
    @classmethod
    def _validate_refresh_interval(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("refresh_interval must be positive")
        return value

    @field_validator("log_retention")
    @classmethod
    def _validate_retention(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("log_retention must be positive")
        return value


class AppConfig(BaseModel):
    """Root configuration model."""

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
        config = AppConfig.model_validate(raw)
    except PydanticValidationError as exc:
        errors = [ValidationError("/".join(str(loc) for loc in err["loc"]), err["msg"]) for err in exc.errors()]
        return ConfigResult(config=None, errors=errors)

    normalized_symbols, symbol_errors = validate_symbols(config.trading.symbols)
    errors = collect_errors(
        symbol_errors,
        validate_positive(config.trading.initial_capital, "trading.initial_capital"),
        validate_fee(config.fees.maker, "fees.maker"),
        validate_fee(config.fees.taker, "fees.taker"),
    )

    if errors:
        return ConfigResult(config=None, errors=errors)

    config = config.model_copy(
        update={
            "trading": config.trading.model_copy(update={"symbols": normalized_symbols})
        }
    )

    return ConfigResult(config=config, errors=[])


def redact_config(config: AppConfig) -> Dict[str, Any]:
    data = config.model_dump()
    data["api"]["kraken_key"] = "***"
    data["api"]["kraken_secret"] = "***"
    if data["api"].get("discord_webhook"):
        data["api"]["discord_webhook"] = "***"
    return data
