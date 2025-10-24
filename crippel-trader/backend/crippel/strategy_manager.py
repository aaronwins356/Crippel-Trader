"""Strategy management system for coordinating multiple trading strategies."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Type
from collections import defaultdict

import structlog
import numpy as np

from .config import get_settings
from .models.core import PriceTick, Order, OrderSide, OrderType, Mode
from .strategies.base import BaseStrategy, StrategySignal, SignalType
from .strategies.technical import RSIStrategy, MACDStrategy, MomentumStrategy, BollingerBandsStrategy, MultiTimeframeStrategy
from .strategies.arbitrage import ArbitrageStrategy, CrossExchangeArbitrageStrategy, TriangularArbitrageStrategy
from .strategies.market_making import MarketMakingStrategy, AdaptiveMarketMakingStrategy
from .notifications import get_notification_service
from .risk_manager import RiskManager
from .paper_trading import PaperTradingEngine


class StrategyManager:
    """Manages multiple trading strategies and coordinates their signals."""
    
    def __init__(self, paper_trading_engine: PaperTradingEngine, risk_manager: RiskManager):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        self.notification_service = get_notification_service()
        self.paper_trading_engine = paper_trading_engine
        self.risk_manager = risk_manager
        
        # Strategy registry
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_weights: Dict[str, float] = {}
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}
        
        # Signal aggregation
        self.recent_signals: Dict[str, List[StrategySignal]] = defaultdict(list)
        self.signal_history: List[StrategySignal] = []
        self.executed_orders: List[Order] = []
        
        # Strategy allocation
        self.strategy_allocations: Dict[str, float] = {}
        self.total_allocation = 1.0
        
        # Performance tracking
        self.strategy_pnl: Dict[str, float] = defaultdict(float)
        self.strategy_trades: Dict[str, int] = defaultdict(int)
        self.strategy_win_rates: Dict[str, float] = defaultdict(float)
        
        # Initialize default strategies (will be done during startup)
        self._strategies_initialized = False
    
    async def _initialize_default_strategies(self) -> None:
        """Initialize default trading strategies."""
        try:
            symbols = self.settings.supported_crypto_pairs + self.settings.supported_stock_symbols
            
            # Technical analysis strategies
            await self.add_strategy(RSIStrategy(symbols, {"rsi_period": 14, "oversold_threshold": 30, "overbought_threshold": 70}), weight=0.15)
            await self.add_strategy(MACDStrategy(symbols, {"fast_period": 12, "slow_period": 26}), weight=0.15)
            await self.add_strategy(MomentumStrategy(symbols, {"short_period": 10, "long_period": 30}), weight=0.15)
            await self.add_strategy(BollingerBandsStrategy(symbols, {"bb_period": 20, "bb_std_dev": 2.0}), weight=0.10)
            await self.add_strategy(MultiTimeframeStrategy(symbols, {"fast_ma": 10, "medium_ma": 20, "slow_ma": 50}), weight=0.10)
            
            # Arbitrage strategies
            await self.add_strategy(ArbitrageStrategy(symbols, {"correlation_threshold": 0.7, "zscore_entry": 2.0}), weight=0.10)
            await self.add_strategy(CrossExchangeArbitrageStrategy(symbols, {"min_profit_threshold": 0.005}), weight=0.05)
            await self.add_strategy(TriangularArbitrageStrategy(symbols, {"min_profit_threshold": 0.003}), weight=0.05)
            
            # Market making strategies
            await self.add_strategy(MarketMakingStrategy(symbols, {"base_spread": 0.002, "inventory_limit": 0.1}), weight=0.10)
            await self.add_strategy(AdaptiveMarketMakingStrategy(symbols, {"learning_rate": 0.01, "profit_target": 0.001}), weight=0.05)
            
            self.logger.info("Default strategies initialized", strategy_count=len(self.strategies))
            
            await self.notification_service.send_system_alert(
                "Strategy Manager Initialized",
                f"Loaded {len(self.strategies)} trading strategies",
                "success"
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize default strategies", error=str(e))
            await self.notification_service.send_system_alert(
                "Strategy Initialization Failed",
                f"Error loading strategies: {str(e)}",
                "error"
            )
    
    async def add_strategy(self, strategy: BaseStrategy, weight: float = 0.1, allocation: float = 0.1) -> None:
        """Add a new strategy to the manager."""
        strategy_name = strategy.name
        
        if strategy_name in self.strategies:
            self.logger.warning("Strategy already exists, replacing", name=strategy_name)
        
        self.strategies[strategy_name] = strategy
        self.strategy_weights[strategy_name] = weight
        self.strategy_allocations[strategy_name] = allocation
        self.strategy_performance[strategy_name] = {
            "total_signals": 0,
            "profitable_signals": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "last_signal": None,
            "created_at": datetime.utcnow(),
            "is_active": True,
        }
        
        self.logger.info("Strategy added", name=strategy_name, weight=weight, allocation=allocation)
        
        await self.notification_service.send_strategy_alert(
            strategy_name,
            "created",
            details=f"Weight: {weight:.1%}, Allocation: {allocation:.1%}"
        )
    
    async def remove_strategy(self, strategy_name: str) -> bool:
        """Remove a strategy from the manager."""
        if strategy_name not in self.strategies:
            return False
        
        # Deactivate strategy first
        self.strategies[strategy_name].deactivate()
        
        # Remove from all tracking
        del self.strategies[strategy_name]
        del self.strategy_weights[strategy_name]
        del self.strategy_allocations[strategy_name]
        del self.strategy_performance[strategy_name]
        
        self.logger.info("Strategy removed", name=strategy_name)
        
        await self.notification_service.send_strategy_alert(
            strategy_name,
            "removed"
        )
        
        return True
    
    async def update_strategy_weight(self, strategy_name: str, new_weight: float) -> bool:
        """Update the weight of a strategy."""
        if strategy_name not in self.strategies:
            return False
        
        old_weight = self.strategy_weights[strategy_name]
        self.strategy_weights[strategy_name] = new_weight
        
        self.logger.info("Strategy weight updated", name=strategy_name, old_weight=old_weight, new_weight=new_weight)
        return True
    
    async def activate_strategy(self, strategy_name: str) -> bool:
        """Activate a strategy."""
        if strategy_name not in self.strategies:
            return False
        
        self.strategies[strategy_name].activate()
        self.strategy_performance[strategy_name]["is_active"] = True
        
        await self.notification_service.send_strategy_alert(
            strategy_name,
            "activated"
        )
        
        return True
    
    async def deactivate_strategy(self, strategy_name: str) -> bool:
        """Deactivate a strategy."""
        if strategy_name not in self.strategies:
            return False
        
        self.strategies[strategy_name].deactivate()
        self.strategy_performance[strategy_name]["is_active"] = False
        
        await self.notification_service.send_strategy_alert(
            strategy_name,
            "deactivated"
        )
        
        return True
    
    async def process_market_data(self, tick: PriceTick) -> Optional[Order]:
        """Process market data through all strategies and generate orders."""
        try:
            # Collect signals from all active strategies
            signals = []
            
            for strategy_name, strategy in self.strategies.items():
                if strategy.is_active:
                    try:
                        signal = await strategy.update_market_data(tick)
                        if signal:
                            signals.append((strategy_name, signal))
                            self.recent_signals[tick.symbol].append(signal)
                            self.signal_history.append(signal)
                            
                            # Keep recent signals manageable
                            if len(self.recent_signals[tick.symbol]) > 100:
                                self.recent_signals[tick.symbol] = self.recent_signals[tick.symbol][-100:]
                            
                            if len(self.signal_history) > 1000:
                                self.signal_history = self.signal_history[-1000:]
                    
                    except Exception as e:
                        self.logger.error("Strategy error", strategy=strategy_name, error=str(e))
                        continue
            
            if not signals:
                return None
            
            # Aggregate signals
            aggregated_signal = await self._aggregate_signals(signals, tick)
            
            if aggregated_signal:
                # Generate order from aggregated signal
                order = await self._generate_order_from_signal(aggregated_signal, tick)
                
                if order:
                    # Validate order with risk manager
                    portfolio = self.paper_trading_engine.get_portfolio_state()
                    current_prices = {tick.symbol: tick}
                    
                    is_valid, error_msg = await self.risk_manager.validate_order(order, portfolio, current_prices)
                    
                    if is_valid:
                        # Submit order to paper trading engine
                        success = await self.paper_trading_engine.submit_order(order)
                        
                        if success:
                            self.executed_orders.append(order)
                            self.logger.info("Order executed", order=order)
                            return order
                        else:
                            self.logger.warning("Order submission failed", order=order)
                    else:
                        self.logger.warning("Order rejected by risk manager", order=order, reason=error_msg)
            
            return None
            
        except Exception as e:
            self.logger.error("Error processing market data", error=str(e))
            return None
    
    async def _aggregate_signals(self, signals: List[tuple[str, StrategySignal]], tick: PriceTick) -> Optional[StrategySignal]:
        """Aggregate multiple strategy signals into a single signal."""
        if not signals:
            return None
        
        # Separate by signal type
        buy_signals = [(name, sig) for name, sig in signals if sig.signal == SignalType.BUY]
        sell_signals = [(name, sig) for name, sig in signals if sig.signal == SignalType.SELL]
        
        # Calculate weighted scores
        buy_score = 0.0
        sell_score = 0.0
        total_confidence = 0.0
        
        for strategy_name, signal in buy_signals:
            weight = self.strategy_weights.get(strategy_name, 0.1)
            weighted_strength = signal.strength * signal.confidence * weight
            buy_score += weighted_strength
            total_confidence += signal.confidence * weight
        
        for strategy_name, signal in sell_signals:
            weight = self.strategy_weights.get(strategy_name, 0.1)
            weighted_strength = abs(signal.strength) * signal.confidence * weight
            sell_score += weighted_strength
            total_confidence += signal.confidence * weight
        
        # Determine final signal
        net_score = buy_score - sell_score
        min_threshold = 0.1  # Minimum threshold for signal generation
        
        if abs(net_score) < min_threshold:
            return None
        
        # Create aggregated signal
        if net_score > 0:
            signal_type = SignalType.BUY
            strength = min(1.0, net_score)
        else:
            signal_type = SignalType.SELL
            strength = min(1.0, abs(net_score))
        
        confidence = min(0.95, total_confidence / len(signals))
        
        # Collect metadata from contributing strategies
        contributing_strategies = [name for name, _ in signals]
        
        return StrategySignal(
            symbol=tick.symbol,
            signal=signal_type,
            strength=strength,
            confidence=confidence,
            price=tick.price,
            timestamp=tick.ts,
            metadata={
                "aggregated": True,
                "contributing_strategies": contributing_strategies,
                "buy_score": buy_score,
                "sell_score": sell_score,
                "net_score": net_score,
                "signal_count": len(signals),
            }
        )
    
    async def _generate_order_from_signal(self, signal: StrategySignal, tick: PriceTick) -> Optional[Order]:
        """Generate an order from an aggregated signal."""
        try:
            # Calculate position size based on signal strength and risk parameters
            portfolio = self.paper_trading_engine.get_portfolio_state()
            current_equity = portfolio.equity
            
            # Base position size as percentage of equity
            base_position_pct = 0.02  # 2% base position
            
            # Adjust based on signal strength and confidence
            strength_multiplier = signal.strength
            confidence_multiplier = signal.confidence
            aggression_multiplier = self.settings.get_position_size_multiplier(self.paper_trading_engine.current_aggression)
            
            position_pct = base_position_pct * strength_multiplier * confidence_multiplier * aggression_multiplier
            position_value = current_equity * position_pct
            
            # Calculate quantity
            quantity = position_value / signal.price
            
            # Minimum order size check
            min_order_value = 10.0  # $10 minimum
            if position_value < min_order_value:
                return None
            
            # Determine order type and price
            if signal.strength > 0.8 and signal.confidence > 0.8:
                # High confidence - use market order
                order_type = OrderType.MARKET
                order_price = signal.price
            else:
                # Lower confidence - use limit order with small buffer
                order_type = OrderType.LIMIT
                if signal.signal == SignalType.BUY:
                    order_price = signal.price * 0.999  # Slightly below market
                else:
                    order_price = signal.price * 1.001  # Slightly above market
            
            # Generate unique order ID
            order_id = f"strat_{int(datetime.utcnow().timestamp() * 1000)}"
            
            order = Order(
                id=order_id,
                symbol=signal.symbol,
                side=OrderSide.BUY if signal.signal == SignalType.BUY else OrderSide.SELL,
                type=order_type,
                size=quantity,
                price=order_price,
                ts=signal.timestamp,
                mode=Mode.PAPER,
                aggression=self.paper_trading_engine.current_aggression
            )
            
            return order
            
        except Exception as e:
            self.logger.error("Error generating order from signal", signal=signal, error=str(e))
            return None
    
    async def update_strategy_performance(self, strategy_name: str, pnl: float, is_profitable: bool) -> None:
        """Update performance metrics for a strategy."""
        if strategy_name not in self.strategy_performance:
            return
        
        perf = self.strategy_performance[strategy_name]
        perf["total_signals"] += 1
        perf["total_pnl"] += pnl
        
        if is_profitable:
            perf["profitable_signals"] += 1
        
        perf["win_rate"] = perf["profitable_signals"] / perf["total_signals"]
        
        # Update strategy object performance
        if strategy_name in self.strategies:
            self.strategies[strategy_name].update_performance(pnl, is_profitable)
        
        # Track for rebalancing
        self.strategy_pnl[strategy_name] += pnl
        self.strategy_trades[strategy_name] += 1
        self.strategy_win_rates[strategy_name] = perf["win_rate"]
    
    async def rebalance_strategies(self) -> None:
        """Rebalance strategy weights based on performance."""
        if len(self.strategies) < 2:
            return
        
        try:
            # Calculate performance scores
            performance_scores = {}
            
            for strategy_name in self.strategies:
                if self.strategy_trades[strategy_name] < 10:  # Need minimum trades
                    performance_scores[strategy_name] = 0.5  # Neutral score
                    continue
                
                # Combine multiple metrics
                pnl_score = max(0, min(1, (self.strategy_pnl[strategy_name] / 100) + 0.5))  # Normalize around 0.5
                win_rate_score = self.strategy_win_rates[strategy_name]
                
                # Weighted combination
                performance_scores[strategy_name] = (pnl_score * 0.6) + (win_rate_score * 0.4)
            
            # Normalize scores to sum to 1
            total_score = sum(performance_scores.values())
            if total_score > 0:
                for strategy_name in performance_scores:
                    new_weight = performance_scores[strategy_name] / total_score
                    
                    # Smooth weight changes (don't change too drastically)
                    old_weight = self.strategy_weights[strategy_name]
                    smoothed_weight = old_weight * 0.8 + new_weight * 0.2
                    
                    # Apply minimum and maximum weight constraints
                    smoothed_weight = max(0.01, min(0.5, smoothed_weight))  # 1% to 50%
                    
                    self.strategy_weights[strategy_name] = smoothed_weight
            
            self.logger.info("Strategy weights rebalanced", weights=self.strategy_weights)
            
            await self.notification_service.send_system_alert(
                "Strategy Rebalancing",
                f"Rebalanced {len(self.strategies)} strategy weights based on performance",
                "info"
            )
            
        except Exception as e:
            self.logger.error("Error rebalancing strategies", error=str(e))
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get summary of all strategies and their performance."""
        summary = {
            "total_strategies": len(self.strategies),
            "active_strategies": len([s for s in self.strategies.values() if s.is_active]),
            "total_signals_today": len([s for s in self.signal_history if s.timestamp.date() == datetime.utcnow().date()]),
            "total_orders_executed": len(self.executed_orders),
            "strategies": {}
        }
        
        for name, strategy in self.strategies.items():
            perf = self.strategy_performance.get(name, {})
            summary["strategies"][name] = {
                "name": name,
                "is_active": strategy.is_active,
                "weight": self.strategy_weights.get(name, 0.0),
                "allocation": self.strategy_allocations.get(name, 0.0),
                "total_signals": perf.get("total_signals", 0),
                "win_rate": perf.get("win_rate", 0.0),
                "total_pnl": perf.get("total_pnl", 0.0),
                "last_signal": perf.get("last_signal"),
                "recent_signals": len([s for s in self.signal_history if s.timestamp > datetime.utcnow() - timedelta(hours=1)]),
            }
        
        return summary
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        for strategy in self.strategies.values():
            strategy.deactivate()
        
        self.logger.info("Strategy manager cleaned up")