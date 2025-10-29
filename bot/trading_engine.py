"""Core trading engine with strict validation and logging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from utils.kraken import kraken_round, normalize_symbol
from utils.logger import get_logger

from .config_loader import AppConfig
from .state import BotState, Position, Trade


class TradingError(Exception):
    """Raised when a trade cannot be executed."""


@dataclass
class RiskLimits:
    max_position_pct: float
    max_daily_loss_pct: float


class TradingEngine:
    def __init__(self, config: AppConfig, state: BotState, log_dir: Path) -> None:
        self.config = config
        self.state = state
        self.logger = get_logger("trading", log_dir, level=config.runtime.log_level, retention=config.runtime.log_retention)
        self.risk = RiskLimits(
            max_position_pct=config.trading.max_position_pct,
            max_daily_loss_pct=config.trading.max_daily_loss_pct,
        )
        self._live_trade_hook: Callable[[Trade], None] | None = None

    def set_live_trade_hook(self, callback: Callable[[Trade], None]) -> None:
        self._live_trade_hook = callback

    def _validate_symbol(self, symbol: str) -> str:
        normalized = normalize_symbol(symbol)
        if normalized not in self.config.trading.pairs:
            raise TradingError(f"Symbol {symbol} not enabled in configuration")
        return normalized

    def _ensure_balance(self, cost: float) -> None:
        if cost > self.state.balance:
            raise TradingError("Insufficient balance for requested trade size")

    def _check_risk(self, symbol: str, size: float, price: float, side: str) -> None:
        notional = abs(size) * price
        max_notional = self.config.trading.capital * self.risk.max_position_pct
        if notional > max_notional:
            raise TradingError(
                f"Trade size exceeds max position notional ({notional:.2f} > {max_notional:.2f})"
            )
        if self.state.daily_realized_pnl < 0:
            projected_loss = abs(self.state.daily_realized_pnl) / self.config.trading.capital
            if projected_loss >= self.risk.max_daily_loss_pct:
                raise TradingError("Daily loss limit reached. Trading halted.")

    def _calculate_fee(self, symbol: str, size: float, price: float, taker: bool) -> float:
        rate = self.config.fees.taker if taker else self.config.fees.maker
        raw_fee = abs(size) * price * rate
        rounded = kraken_round(raw_fee, symbol, is_size=False)
        return rounded

    def submit_order(self, symbol: str, side: str, size: float, price: float, taker: bool = True) -> Trade:
        if size <= 0:
            raise TradingError("Order size must be positive")
        if price <= 0:
            raise TradingError("Order price must be positive")

        normalized = self._validate_symbol(symbol)
        rounded_size = kraken_round(size, normalized, is_size=True)
        rounded_price = kraken_round(price, normalized, is_size=False)

        if rounded_size <= 0:
            raise TradingError("Rounded order size is zero; adjust lot size")

        notional = rounded_size * rounded_price
        if side.lower() == "buy":
            self._ensure_balance(notional)
        self._check_risk(normalized, rounded_size, rounded_price, side)

        fee = self._calculate_fee(normalized, rounded_size, rounded_price, taker)
        total_cost = notional + fee if side.lower() == "buy" else notional - fee

        if self.config.runtime.read_only or self.config.trading.mode == "paper":
            self.logger.info("Read-only trade simulated: %s %s %s @ %s", side, rounded_size, normalized, rounded_price)
        else:
            self.logger.info("Executing live trade: %s %s %s @ %s", side, rounded_size, normalized, rounded_price)
            if self._live_trade_hook:
                self._live_trade_hook(
                    Trade(
                        timestamp=datetime.utcnow(),
                        symbol=normalized,
                        side=side,
                        size=rounded_size,
                        price=rounded_price,
                        fee=fee,
                        total_cost=total_cost,
                    )
                )

        position = self.state.positions.get(normalized)
        if side.lower() == "buy":
            if position:
                new_size = position.size + rounded_size
                avg_price = (
                    (position.size * position.avg_price + rounded_size * rounded_price) / new_size
                )
                position.size = new_size
                position.avg_price = avg_price
            else:
                self.state.positions[normalized] = Position(symbol=normalized, size=rounded_size, avg_price=rounded_price)
        else:
            if not position or position.size < rounded_size:
                raise TradingError("Cannot sell more than current position size")
            realized = (rounded_price - position.avg_price) * rounded_size
            self.state.daily_realized_pnl += realized - fee
            position.size -= rounded_size
            if position.size == 0:
                del self.state.positions[normalized]

        self.state.balance -= total_cost if side.lower() == "buy" else -total_cost

        trade = Trade(
            timestamp=datetime.utcnow(),
            symbol=normalized,
            side=side,
            size=rounded_size,
            price=rounded_price,
            fee=fee,
            total_cost=total_cost,
        )
        self.state.trades.append(trade)
        self.state.total_fees_paid += fee
        self.logger.info("Trade recorded: %s", trade)
        return trade
