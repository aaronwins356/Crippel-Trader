"""In-memory state containers for the trading system."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..config import get_settings
from ..engine.params import tune_params
from ..engine.portfolio import Portfolio
from ..engine.risk import RiskManager
from ..models.core import AggressionParams, ModeState, PortfolioState, RiskLimits, TradeStat
from ..models.enums import Mode


@dataclass
class EngineState:
    """Current system state shared across components."""

    portfolio: Portfolio
    stats: TradeStat
    aggression: AggressionParams
    mode_state: ModeState
    listeners: list[Callable[[PortfolioState], None]] = field(default_factory=list)

    def update_portfolio(self, snapshot: PortfolioState) -> None:
        for listener in self.listeners:
            listener(snapshot)


class StateService:
    """Manages shared state and configuration updates."""

    def __init__(self) -> None:
        settings = get_settings()
        aggression = tune_params(settings.default_aggression)
        portfolio = Portfolio(starting_cash=10000.0, mode=Mode.PAPER)
        risk_limits = RiskLimits(
            per_trade_cap=settings.per_trade_cap,
            per_symbol_exposure=settings.per_symbol_exposure,
            drawdown_limit=settings.drawdown_limit,
        )
        self.state = EngineState(
            portfolio=portfolio,
            stats=TradeStat(total_trades=0, winning_trades=0, losing_trades=0, fees_paid=0.0, realized_pnl=0.0),
            aggression=aggression,
            mode_state=ModeState(mode=Mode.PAPER, live_confirmed=False),
        )
        self.risk = RiskManager(risk_limits)
        self._lock = asyncio.Lock()

    async def set_aggression(self, aggression: int) -> AggressionParams:
        params = tune_params(aggression)
        async with self._lock:
            self.state.aggression = params
        return params

    async def set_mode(self, mode: Mode, confirmed: bool) -> ModeState:
        async with self._lock:
            self.state.mode_state = ModeState(mode=mode, live_confirmed=confirmed)
            self.state.portfolio.set_mode(mode)
        return self.state.mode_state

    def record_trade(self, pnl: float, fee: float) -> None:
        stats = self.state.stats
        stats.total_trades += 1
        if pnl >= 0:
            stats.winning_trades += 1
        else:
            stats.losing_trades += 1
        stats.realized_pnl += pnl
        stats.fees_paid += fee

    def snapshot(self, ts: datetime) -> PortfolioState:
        return self.state.portfolio.snapshot(ts)
