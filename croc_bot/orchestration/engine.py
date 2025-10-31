"""Trading engine orchestrating all modules."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..data_feed import DataFeed, SyntheticFeedConfig, SyntheticPriceFeed
from ..execution import ExecutionClient, SimulationConfig, SimulationExecutionClient
from ..execution.base import ExecutionResult, OrderStatus
from ..monitoring import (
    BaseMonitor,
    CompositeMonitor,
    MetricsMonitor,
    NoOpMonitor,
    StructuredLoggingMonitor,
    configure_logging,
)
from ..risk import BaseRiskManager, SimpleRiskConfig, SimpleRiskManager
from ..strategy import BaseStrategy, MovingAverageConfig, MovingAverageStrategy
from ..domain import TradeSignal
from .config import BotConfig


@dataclass(slots=True)
class TradingEngineDependencies:
    feed: DataFeed
    strategy: BaseStrategy
    execution: ExecutionClient
    risk: BaseRiskManager
    monitor: BaseMonitor


class TradingEngine:
    """Coordinates data ingestion, strategy logic, risk, and execution."""

    def __init__(self, deps: TradingEngineDependencies) -> None:
        self._feed = deps.feed
        self._strategy = deps.strategy
        self._execution = deps.execution
        self._risk = deps.risk
        self._monitor = deps.monitor
        self._shutdown = asyncio.Event()

    async def run(self, *, max_steps: int | None = None) -> None:
        steps = 0
        try:
            async for market in self._feed.stream():
                if max_steps is not None and steps >= max_steps:
                    break
                steps += 1
                portfolio = self._execution.update_market(market)
                self._monitor.on_tick(market, portfolio)
                raw_action = self._strategy.on_market_data(market, portfolio)
                adjusted_action = self._risk.evaluate(raw_action, market, portfolio)
                self._monitor.on_action(raw_action, adjusted_action)

                if adjusted_action.signal != TradeSignal.HOLD:
                    result = await self._execution.execute(adjusted_action, market)
                    self._monitor.on_execution(result)
                else:
                    self._monitor.on_execution(
                        ExecutionResult(
                            action=adjusted_action,
                            status=OrderStatus.SKIPPED,
                            filled_units=0.0,
                            notional_value=0.0,
                            fee_paid=0.0,
                            portfolio=portfolio,
                        )
                    )

                if self._shutdown.is_set():
                    break
        except Exception as exc:  # pragma: no cover - defensive
            self._monitor.on_error(exc)
            raise
        finally:
            self._monitor.flush()

    def stop(self) -> None:
        self._shutdown.set()

class TradingEngineBuilder:
    """Factory responsible for wiring dependencies."""

    def __init__(self, config: BotConfig) -> None:
        self._config = config

    def build(self) -> TradingEngine:
        feed = self._build_feed()
        execution = self._build_execution()
        strategy = self._build_strategy()
        risk = self._build_risk()
        monitor = self._build_monitor()
        deps = TradingEngineDependencies(
            feed=feed,
            strategy=strategy,
            execution=execution,
            risk=risk,
            monitor=monitor,
        )
        return TradingEngine(deps)

    def _build_feed(self) -> DataFeed:
        feed_cfg = self._config.feed
        synthetic = SyntheticFeedConfig(
            symbol=feed_cfg.symbol,
            interval_seconds=feed_cfg.interval_seconds,
            initial_price=feed_cfg.initial_price,
            volatility=feed_cfg.volatility,
            seed=feed_cfg.seed,
        )
        return SyntheticPriceFeed(synthetic)

    def _build_strategy(self) -> BaseStrategy:
        strat_cfg = self._config.strategy
        if strat_cfg.type == "moving_average":
            config = MovingAverageConfig(
                fast_window=strat_cfg.fast_window,
                slow_window=strat_cfg.slow_window,
                target_notional=strat_cfg.target_notional,
            )
            return MovingAverageStrategy(config)
        raise ValueError(f"Unsupported strategy type: {strat_cfg.type}")

    def _build_execution(self) -> ExecutionClient:
        exec_cfg = self._config.execution or self._default_execution_settings()
        config = SimulationConfig(
            starting_balance=exec_cfg.starting_balance,
            trading_fee_bps=exec_cfg.trading_fee_bps,
        )
        return SimulationExecutionClient(config)

    def _build_risk(self) -> BaseRiskManager:
        risk_cfg = self._config.risk
        if risk_cfg.type == "simple":
            config = SimpleRiskConfig(
                max_drawdown=risk_cfg.max_drawdown,
                stop_loss_pct=risk_cfg.stop_loss_pct,
                position_size_pct=risk_cfg.position_size_pct,
                max_position_value=risk_cfg.max_position_value,
            )
            return SimpleRiskManager(config)
        raise ValueError(f"Unsupported risk type: {risk_cfg.type}")

    def _build_monitor(self) -> BaseMonitor:
        monitors: list[BaseMonitor] = []
        monitoring_cfg = self._config.monitoring
        if monitoring_cfg.logging_enabled:
            configure_logging()
            monitors.append(StructuredLoggingMonitor())
        if monitoring_cfg.metrics_enabled:
            monitors.append(MetricsMonitor())
        if not monitors:
            return NoOpMonitor()
        if len(monitors) == 1:
            return monitors[0]
        return CompositeMonitor(monitors)

    def _default_execution_settings(self):
        from .config import SimulationExecutionSettings

        return SimulationExecutionSettings(starting_balance=10_000.0, trading_fee_bps=5)
