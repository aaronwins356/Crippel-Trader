"""Core trading engine with strict validation and logging."""

from __future__ import annotations

import asyncio
import json
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
    """Derived risk constraints for the trading engine."""

    max_single_trade_fraction: float
    max_portfolio_fraction: float
    max_daily_loss_fraction: float
    stop_loss_buffer: float


class TradingEngine:
    def __init__(self, config: AppConfig, state: BotState, log_dir: Path) -> None:
        self.config = config
        self.state = state
        self.logger = get_logger(
            "trading",
            log_dir,
            level=config.runtime.log_level,
            retention=config.runtime.log_retention,
        )
        aggression = config.trading.aggression
        self.initial_capital = config.trading.initial_capital
        self.risk = RiskLimits(
            max_single_trade_fraction=min(0.01 * aggression, 0.2),
            max_portfolio_fraction=min(0.3 + 0.05 * aggression, 0.9),
            max_daily_loss_fraction=min(0.02 + 0.005 * aggression, 0.15),
            stop_loss_buffer=max(0.005, 0.02 - 0.001 * aggression),
        )
        self._live_trade_hook: Callable[[Trade], None] | None = None
        self._trades_path = log_dir / "trades.jsonl"
        self._trades_path.parent.mkdir(parents=True, exist_ok=True)

    def set_live_trade_hook(self, callback: Callable[[Trade], None]) -> None:
        self._live_trade_hook = callback

    def _validate_symbol(self, symbol: str) -> str:
        normalized = normalize_symbol(symbol)
        if normalized not in self.config.trading.symbols:
            raise TradingError(f"Symbol {symbol} not enabled in configuration")
        return normalized

    def _ensure_balance(self, cost: float) -> None:
        if cost > self.state.balance:
            raise TradingError("Insufficient balance for requested trade size")

    def _check_risk(self, size: float, price: float, side: str) -> None:
        notional = abs(size) * price
        max_single_trade = self.initial_capital * self.risk.max_single_trade_fraction
        if notional > max_single_trade:
            raise TradingError(
                f"Trade size exceeds allocation cap ({notional:.2f} > {max_single_trade:.2f})"
            )

        projected_deployed = self.state.deployed_capital
        if side.lower() == "buy":
            projected_deployed += notional
        else:
            projected_deployed = max(0.0, projected_deployed - notional)

        max_portfolio = self.initial_capital * self.risk.max_portfolio_fraction
        if projected_deployed > max_portfolio:
            raise TradingError(
                f"Portfolio allocation exceeded ({projected_deployed:.2f} > {max_portfolio:.2f})"
            )

        if self.state.daily_realized_pnl < 0:
            realized_drawdown = abs(self.state.daily_realized_pnl)
            max_loss = self.initial_capital * self.risk.max_daily_loss_fraction
            if realized_drawdown >= max_loss:
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
        self._check_risk(rounded_size, rounded_price, side)

        fee = self._calculate_fee(normalized, rounded_size, rounded_price, taker)
        total_cost = notional + fee if side.lower() == "buy" else notional - fee

        stop_loss_price = max(0.0, rounded_price * (1 - self.risk.stop_loss_buffer))
        trade_mode = self.config.trading.mode
        capital_used = notional

        if self.config.runtime.read_only_mode or trade_mode == "paper":
            self.logger.info(
                "Read-only trade simulated",
                extra={
                    "side": side,
                    "size": rounded_size,
                    "symbol": normalized,
                    "price": rounded_price,
                    "capital_used": capital_used,
                    "stop_loss": stop_loss_price,
                },
            )
        else:
            self.logger.info(
                "Executing live trade",
                extra={
                    "side": side,
                    "size": rounded_size,
                    "symbol": normalized,
                    "price": rounded_price,
                    "capital_used": capital_used,
                    "stop_loss": stop_loss_price,
                },
            )
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
                        capital_used=capital_used,
                        stop_loss=stop_loss_price,
                        taker=taker,
                        mode=trade_mode,
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
            self.state.deployed_capital += notional
        else:
            if not position or position.size < rounded_size:
                raise TradingError("Cannot sell more than current position size")
            realized = (rounded_price - position.avg_price) * rounded_size
            self.state.daily_realized_pnl += realized - fee
            position.size -= rounded_size
            if position.size == 0:
                del self.state.positions[normalized]
            self.state.deployed_capital = max(0.0, self.state.deployed_capital - notional)

        if side.lower() == "buy":
            self.state.balance -= total_cost
        else:
            self.state.balance += total_cost

        trade = Trade(
            timestamp=datetime.utcnow(),
            symbol=normalized,
            side=side,
            size=rounded_size,
            price=rounded_price,
            fee=fee,
            total_cost=total_cost,
            capital_used=capital_used,
            stop_loss=stop_loss_price,
            taker=taker,
            mode=trade_mode,
        )
        self.state.trades.append(trade)
        self.state.total_fees_paid += fee
        self._append_trade_log(trade)
        self.logger.info(
            "Trade recorded",
            extra={
                "symbol": trade.symbol,
                "side": trade.side,
                "size": trade.size,
                "price": trade.price,
                "fee": trade.fee,
                "capital_used": trade.capital_used,
                "stop_loss": trade.stop_loss,
                "mode": trade.mode,
            },
        )
        return trade

    async def submit_order_async(self, symbol: str, side: str, size: float, price: float, taker: bool = True) -> Trade:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.submit_order(symbol=symbol, side=side, size=size, price=price, taker=taker),
        )

    def _append_trade_log(self, trade: Trade) -> None:
        try:
            with self._trades_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(trade.to_dict(), separators=(",", ":")) + "\n")
        except Exception as exc:
            self.logger.warning("Failed to persist trade log", error=str(exc))
