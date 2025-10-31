"""Configuration management for croc backend."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

import json

try:
    import orjson
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    class _Orjson:
        @staticmethod
        def loads(data: bytes | str):
            if isinstance(data, (bytes, bytearray)):
                data = data.decode("utf-8")
            return json.loads(data)

    orjson = _Orjson()
from pydantic import AliasChoices, BaseModel, Field, ValidationError, field_validator, model_validator
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    from pydantic import BaseModel

    class BaseSettings(BaseModel):
        model_config = {}

    SettingsConfigDict = dict

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - yaml is optional
    yaml = None


class TradingMode(str, Enum):
    """Trading mode supported by the engine."""

    PAPER = "paper"
    LIVE = "live"
    AI_SIMULATION = "ai_simulation"

    @property
    def external_name(self) -> str:
        if self is TradingMode.AI_SIMULATION:
            return "AI_SIMULATION"
        if self is TradingMode.LIVE:
            return "LIVE_TRADING"
        return "PAPER"

    @classmethod
    def from_external(cls, value: str) -> "TradingMode":
        normalized = value.strip().lower()
        if normalized in {"ai_simulation", "simulation", "ai"}:
            return cls.AI_SIMULATION
        if normalized in {"live", "live_trading"}:
            return cls.LIVE
        if normalized in {"paper", "paper_trading"}:
            return cls.PAPER
        raise ValueError(f"Unsupported trading mode: {value}")


class FeedConfig(BaseModel):
    """Configuration for the market data feed."""

    source: str = Field(default="replay", description="feed identifier")
    symbol: str = Field(default="BTC/USDT")
    timeframe: str = Field(default="1m")
    replay_path: Optional[Path] = None


class StrategyConfig(BaseModel):
    """Strategy selection and parameters."""

    name: str = Field(default="rule_sma")
    params: dict[str, Any] = Field(default_factory=dict)


class RiskLimits(BaseModel):
    """Risk thresholds enforced by :class:`RiskManager`."""

    max_position: float = Field(default=1.0, ge=0)
    max_notional: float = Field(default=10_000.0, ge=0)
    max_daily_drawdown: float = Field(default=500.0, ge=0)
    active_model_max_exposure_pct: float = Field(default=1.0, ge=0.0, le=1.0)
    new_model_max_exposure_pct: float = Field(default=0.2, ge=0.0, le=1.0)


class ExecutionConfig(BaseModel):
    """Broker configuration."""

    broker: str = Field(default="paper")
    slippage_bps: float = Field(default=1.0, ge=0)
    fee_bps: float = Field(default=1.0, ge=0)


class StorageConfig(BaseModel):
    """Storage paths for persistence."""

    base_dir: Path = Field(default=Path("./storage"))
    ticks: Path = Field(default=Path("./storage/ticks"))
    trades: Path = Field(default=Path("./storage/trades"))
    metrics: Path = Field(default=Path("./storage/metrics"))

class SimulationConfig(BaseModel):
    """Parameters controlling the AI simulation mode."""

    base_price: float = Field(default=30_000.0, gt=0)
    volatility: float = Field(default=0.002, ge=0)
    interval_seconds: float = Field(default=1.0, gt=0)
    seed: Optional[int] = Field(default=None)
    reconfigure_interval_seconds: float = Field(default=60.0, gt=0)
    min_order_size: float = Field(default=0.001, gt=0)
    max_order_size: float = Field(default=0.05, gt=0)
    max_threshold: float = Field(default=50.0, ge=0)
    threshold_jitter: float = Field(default=0.25, ge=0)
    order_size_jitter: float = Field(default=0.002, ge=0)


class Settings(BaseSettings):
    """Application settings loaded from env + config file."""

    model_config = SettingsConfigDict(env_prefix="CROC_", env_file=".env", env_file_encoding="utf-8")

    mode: TradingMode = Field(
        default=TradingMode.PAPER,
        validation_alias=AliasChoices("MODE", "CROC_MODE"),
    )
    log_level: str = Field(default="INFO")
    config_file: Optional[Path] = Field(default=None, validation_alias="config_file")
    model_active: Optional[Path] = None
    feed: FeedConfig = Field(default_factory=FeedConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskLimits = Field(default_factory=RiskLimits)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)

    exchange: Optional[str] = None
    api_key: Optional[str] = Field(default=None, alias="API_KEY")
    api_secret: Optional[str] = Field(default=None, alias="API_SECRET")
    api_passphrase: Optional[str] = Field(default=None, alias="API_PASSPHRASE")
    simulation_auto_reason: Optional[str] = Field(default=None, exclude=True)

    @field_validator("mode", mode="before")
    @classmethod
    def _normalize_mode(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                return TradingMode.from_external(value)
            except ValueError:
                lower = value.lower()
                if lower in TradingMode._value2member_map_:
                    return TradingMode(lower)
        return value

    @model_validator(mode="after")
    def validate_mode(self) -> "Settings":
        if self.mode is TradingMode.LIVE:
            missing = [
                field
                for field, value in {
                    "exchange": self.exchange,
                    "api_key": self.api_key,
                    "api_secret": self.api_secret,
                }.items()
                if not value
            ]
            if missing:
                exchange = (self.exchange or "").lower()
                if exchange in {"", "kraken"}:
                    self.mode = TradingMode.AI_SIMULATION
                    self.feed.source = "simulation"
                    self.execution.broker = "paper"
                    self.simulation_auto_reason = (
                        "Missing Kraken credentials: " + ", ".join(missing)
                    )
                else:
                    raise ValueError(
                        "Live trading requires credentials: " + ", ".join(missing)
                    )
        if self.mode is TradingMode.AI_SIMULATION:
            self.feed.source = "simulation"
            self.execution.broker = "paper"
        return self

    @classmethod
    def _load_config_file(cls, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Config file {path} not found")
        if path.suffix in {".json"}:
            return orjson.loads(path.read_bytes())
        if path.suffix in {".yml", ".yaml"}:
            if yaml is None:
                raise RuntimeError("pyyaml not installed; cannot load YAML config")
            return yaml.safe_load(path.read_text()) or {}
        raise ValueError(f"Unsupported config format: {path.suffix}")

    @classmethod
    def load(cls, env_file: Optional[Path] = None) -> "Settings":
        """Load settings from optional env file and config file."""

        env_kwargs: dict[str, Any] = {}
        if env_file:
            env_kwargs["_env_file"] = env_file
        settings = cls(**env_kwargs)
        if settings.config_file:
            config_data = cls._load_config_file(Path(settings.config_file))
            merged = settings.model_dump()
            merged.update(config_data)
            try:
                settings = cls.model_validate(merged)
            except ValidationError as exc:
                raise ValueError(f"Invalid configuration: {exc}") from exc
        settings.storage.base_dir.mkdir(parents=True, exist_ok=True)
        settings.storage.ticks.mkdir(parents=True, exist_ok=True)
        settings.storage.trades.mkdir(parents=True, exist_ok=True)
        settings.storage.metrics.mkdir(parents=True, exist_ok=True)
        if settings.mode is TradingMode.AI_SIMULATION:
            message = "⚙️ Running in AI Simulation Mode"
            if settings.simulation_auto_reason:
                message += f" ({settings.simulation_auto_reason})"
            print(message)
        return settings


def load_settings() -> Settings:
    """Public helper used by the app to load settings deterministically."""

    env_file = Path(".env")
    return Settings.load(env_file if env_file.exists() else None)


__all__ = [
    "Settings",
    "TradingMode",
    "FeedConfig",
    "StrategyConfig",
    "RiskLimits",
    "ExecutionConfig",
    "StorageConfig",
    "SimulationConfig",
    "load_settings",
]
