"""Enhanced trading system with real market logic and capital management."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

import structlog

from .config import get_settings
from .real_trading_engine import RealTradingEngine
from .adapters.kraken import KrakenAdapter
from .strategies.technical import (
    RSIStrategy, MACDStrategy, BollingerBandsStrategy, 
    MomentumStrategy, MovingAverageCrossoverStrategy
)
from .strategies.arbitrage import ArbitrageStrategy
from .strategies.market_making import MarketMakingStrategy
from .models.core import Order, OrderSide, OrderType, PriceTick, Signal
from .notifications import get_notification_service
from .risk_manager import RiskManager


@dataclass
class TradingSystemConfig:
    """Configuration for the enhanced trading system."""
    initial_capital: float = 1000.0
    max_positions: int = 5
    enable_real_trading: bool = True  # Set to False for paper trading
    risk_aggression: int = 5  # 1-10 scale
    
    # Strategy allocation (percentages should sum to 1.0)
    strategy_allocation: Dict[str, float] = None
    
    def __post_init__(self):
        if self.strategy_allocation is None:
            self.strategy_allocation = {
                "rsi": 0.20,
                "macd": 0.20,
                "bollinger": 0.15,
                "momentum": 0.15,
                "ma_crossover": 0.15,
                "arbitrage": 0.10,
                "market_making": 0.05
            }


class EnhancedTradingSystem:
    """Enhanced trading system with real market logic."""
    
    def __init__(self, config: TradingSystemConfig = None):
        self.config = config or TradingSystemConfig()
        self.logger = structlog.get_logger(__name__)
        self.notification_service = get_notification_service()
        
        # Initialize trading engine
        self.trading_engine = RealTradingEngine(self.config.initial_capital)
        
        # Initialize market data adapter
        self.market_adapter = KrakenAdapter()
        
        # Initialize risk manager
        self.risk_manager = RiskManager()
        
        # Initialize strategies
        self.strategies = self._initialize_strategies()
        
        # Trading state
        self.is_running = False
        self.subscribed_symbols: Set[str] = set()
        self.strategy_signals: Dict[str, List[Signal]] = {}
        
        # Performance tracking
        self.trades_today = 0
        self.max_trades_per_day = 50
        
        self.logger.info("Enhanced trading system initialized",
                        initial_capital=self.config.initial_capital,
                        strategies=list(self.strategies.keys()),
                        real_trading=self.config.enable_real_trading)
    
    def _initialize_strategies(self) -> Dict[str, object]:
        """Initialize trading strategies with proper capital allocation."""
        strategies = {}
        
        # Calculate capital per strategy
        total_capital = self.config.initial_capital
        
        # Technical strategies
        if self.config.strategy_allocation.get("rsi", 0) > 0:
            rsi_capital = total_capital * self.config.strategy_allocation["rsi"]
            strategies["rsi"] = RSIStrategy(
                rsi_period=14,
                oversold_threshold=30,
                overbought_threshold=70,
                max_position_size=rsi_capital * 0.1  # 10% of allocated capital per trade
            )
        
        if self.config.strategy_allocation.get("macd", 0) > 0:
            macd_capital = total_capital * self.config.strategy_allocation["macd"]
            strategies["macd"] = MACDStrategy(
                fast_period=12,
                slow_period=26,
                signal_period=9,
                max_position_size=macd_capital * 0.1
            )
        
        if self.config.strategy_allocation.get("bollinger", 0) > 0:
            bb_capital = total_capital * self.config.strategy_allocation["bollinger"]
            strategies["bollinger"] = BollingerBandsStrategy(
                period=20,
                std_dev=2.0,
                max_position_size=bb_capital * 0.1
            )
        
        if self.config.strategy_allocation.get("momentum", 0) > 0:
            momentum_capital = total_capital * self.config.strategy_allocation["momentum"]
            strategies["momentum"] = MomentumStrategy(
                lookback_period=10,
                momentum_threshold=0.02,
                max_position_size=momentum_capital * 0.1
            )
        
        if self.config.strategy_allocation.get("ma_crossover", 0) > 0:
            ma_capital = total_capital * self.config.strategy_allocation["ma_crossover"]
            strategies["ma_crossover"] = MovingAverageCrossoverStrategy(
                fast_period=10,
                slow_period=30,
                max_position_size=ma_capital * 0.1
            )
        
        # Advanced strategies
        if self.config.strategy_allocation.get("arbitrage", 0) > 0:
            arb_capital = total_capital * self.config.strategy_allocation["arbitrage"]
            strategies["arbitrage"] = ArbitrageStrategy(
                min_profit_bps=10,  # Minimum 0.1% profit
                max_position_size=arb_capital * 0.2
            )
        
        if self.config.strategy_allocation.get("market_making", 0) > 0:
            mm_capital = total_capital * self.config.strategy_allocation["market_making"]
            strategies["market_making"] = MarketMakingStrategy(
                spread_bps=20,  # 0.2% spread
                max_position_size=mm_capital * 0.05,
                inventory_target=0.0
            )
        
        return strategies
    
    async def start(self, symbols: List[str]) -> None:
        """Start the enhanced trading system."""
        if self.is_running:
            self.logger.warning("Trading system already running")
            return
        
        self.logger.info("Starting enhanced trading system", symbols=symbols)
        
        # Validate symbols and check market hours
        valid_symbols = []
        for symbol in symbols:
            if self.trading_engine.is_market_open(symbol):
                valid_symbols.append(symbol)
                self.subscribed_symbols.add(symbol)
            else:
                self.logger.warning("Market closed for symbol", symbol=symbol)
        
        if not valid_symbols:
            raise ValueError("No valid symbols with open markets")
        
        # Start market data feed
        self.is_running = True
        
        # Send startup notification
        await self.notification_service.send_system_alert(
            "Trading System Started",
            f"Real trading system active with ${self.config.initial_capital} capital\n"
            f"Symbols: {', '.join(valid_symbols)}\n"
            f"Strategies: {len(self.strategies)} active",
            "success"
        )
        
        # Start market data processing
        await self._run_market_data_loop(valid_symbols)
    
    async def stop(self) -> None:
        """Stop the trading system."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping enhanced trading system")
        self.is_running = False
        
        # Cancel all open orders
        open_orders = list(self.trading_engine.open_orders.keys())
        for order_id in open_orders:
            await self.trading_engine.cancel_order(order_id)
        
        # Send shutdown notification
        final_equity = self.trading_engine.get_current_equity()
        total_pnl = final_equity - self.config.initial_capital
        
        await self.notification_service.send_system_alert(
            "Trading System Stopped",
            f"Final equity: ${final_equity:.2f}\n"
            f"Total P&L: ${total_pnl:.2f} ({total_pnl/self.config.initial_capital*100:.1f}%)\n"
            f"Trades executed: {self.trades_today}",
            "info"
        )
    
    async def _run_market_data_loop(self, symbols: List[str]) -> None:
        """Main market data processing loop."""
        try:
            async for tick in self.market_adapter.stream_prices(symbols):
                if not self.is_running:
                    break
                
                # Update trading engine with real market data
                await self.trading_engine.update_market_data(tick)
                
                # Process strategies
                await self._process_strategies(tick)
                
                # Check risk limits
                await self._check_risk_limits()
                
        except Exception as e:
            self.logger.error("Error in market data loop", error=str(e))
            await self.notification_service.send_system_alert(
                "Market Data Error",
                f"Error processing market data: {str(e)}",
                "error"
            )
            await self.stop()
    
    async def _process_strategies(self, tick: PriceTick) -> None:
        """Process all strategies for the given price tick."""
        if self.trades_today >= self.max_trades_per_day:
            return  # Daily trade limit reached
        
        # Store tick for strategy analysis
        symbol = tick.symbol
        if symbol not in self.strategy_signals:
            self.strategy_signals[symbol] = []
        
        # Process each strategy
        for strategy_name, strategy in self.strategies.items():
            try:
                # Generate signal
                signal = await strategy.generate_signal(tick)
                
                if signal and signal.strength != 0:
                    self.strategy_signals[symbol].append(signal)
                    
                    # Evaluate if we should trade on this signal
                    should_trade = await self._evaluate_signal(signal, strategy_name)
                    
                    if should_trade:
                        await self._execute_strategy_trade(signal, strategy_name)
                        
            except Exception as e:
                self.logger.error("Error processing strategy", 
                                strategy=strategy_name, 
                                symbol=symbol, 
                                error=str(e))
    
    async def _evaluate_signal(self, signal: Signal, strategy_name: str) -> bool:
        """Evaluate if a signal should result in a trade."""
        # Check signal strength threshold
        min_strength = 0.3  # Minimum 30% signal strength
        if abs(signal.strength) < min_strength:
            return False
        
        # Check if we already have a position in this symbol
        current_position = self.trading_engine.positions.get(signal.symbol)
        if current_position and current_position.size != 0:
            # Don't add to existing positions for now (could be enhanced)
            return False
        
        # Check available capital
        available_cash = self.trading_engine.get_available_cash()
        if available_cash < 100:  # Minimum $100 per trade
            return False
        
        # Check market conditions (simplified)
        if signal.symbol not in self.trading_engine.current_prices:
            return False
        
        current_price = self.trading_engine.current_prices[signal.symbol]
        
        # Check bid/ask spread (don't trade if spread is too wide)
        if current_price.spread > 0 and current_price.spread / current_price.price > 0.01:  # 1% spread limit
            return False
        
        return True
    
    async def _execute_strategy_trade(self, signal: Signal, strategy_name: str) -> None:
        """Execute a trade based on a strategy signal."""
        try:
            # Calculate position size based on signal strength and available capital
            available_cash = self.trading_engine.get_available_cash()
            strategy_allocation = self.config.strategy_allocation.get(strategy_name, 0.1)
            
            # Position size: signal strength * strategy allocation * available cash
            max_trade_value = available_cash * strategy_allocation * abs(signal.strength)
            max_trade_value = min(max_trade_value, available_cash * 0.1)  # Max 10% per trade
            
            current_price = self.trading_engine.current_prices[signal.symbol].price
            position_size = max_trade_value / current_price
            
            # Round to reasonable precision
            position_size = round(position_size, 6)
            
            if position_size * current_price < 10:  # Minimum $10 trade
                return
            
            # Determine order side
            side = OrderSide.BUY if signal.strength > 0 else OrderSide.SELL
            
            # Create order (using limit orders for better execution)
            tick = self.trading_engine.current_prices[signal.symbol]
            
            # Set limit price slightly better than current bid/ask
            if side == OrderSide.BUY:
                limit_price = tick.ask if tick.ask > 0 else current_price
                limit_price *= 1.001  # 0.1% above ask
            else:
                limit_price = tick.bid if tick.bid > 0 else current_price
                limit_price *= 0.999  # 0.1% below bid
            
            order = Order(
                id=str(uuid.uuid4()),
                symbol=signal.symbol,
                side=side,
                type=OrderType.LIMIT,
                size=position_size,
                price=limit_price,
                ts=datetime.utcnow()
            )
            
            # Submit order
            success = await self.trading_engine.submit_order(order)
            
            if success:
                self.trades_today += 1
                self.logger.info("Strategy trade executed",
                               strategy=strategy_name,
                               signal_strength=signal.strength,
                               order=order)
                
                await self.notification_service.send_trade_alert(
                    symbol=signal.symbol,
                    side=side.value,
                    quantity=position_size,
                    price=limit_price,
                    strategy=strategy_name
                )
            
        except Exception as e:
            self.logger.error("Error executing strategy trade",
                            strategy=strategy_name,
                            signal=signal,
                            error=str(e))
    
    async def _check_risk_limits(self) -> None:
        """Check and enforce risk limits."""
        current_equity = self.trading_engine.get_current_equity()
        
        # Check daily loss limit
        daily_loss_pct = self.trading_engine.daily_pnl / self.config.initial_capital
        if daily_loss_pct < -0.05:  # 5% daily loss limit
            await self.stop()
            await self.notification_service.send_system_alert(
                "Daily Loss Limit Reached",
                f"System stopped due to {daily_loss_pct*100:.1f}% daily loss",
                "error"
            )
            return
        
        # Check maximum drawdown
        if self.trading_engine.max_drawdown > 0.15:  # 15% max drawdown
            await self.stop()
            await self.notification_service.send_system_alert(
                "Maximum Drawdown Reached",
                f"System stopped due to {self.trading_engine.max_drawdown*100:.1f}% drawdown",
                "error"
            )
            return
        
        # Check available cash
        if self.trading_engine.get_available_cash() < 50:  # Minimum $50 cash
            # Cancel all open orders to free up cash
            open_orders = list(self.trading_engine.open_orders.keys())
            for order_id in open_orders:
                await self.trading_engine.cancel_order(order_id)
    
    def get_system_status(self) -> Dict:
        """Get current system status."""
        portfolio_state = self.trading_engine.get_portfolio_state()
        
        return {
            "is_running": self.is_running,
            "current_equity": portfolio_state.equity,
            "available_cash": self.trading_engine.get_available_cash(),
            "daily_pnl": portfolio_state.daily_pnl,
            "total_pnl": portfolio_state.total_pnl,
            "max_drawdown": portfolio_state.max_drawdown,
            "trades_today": self.trades_today,
            "open_positions": len([p for p in portfolio_state.positions if p.size != 0]),
            "open_orders": len(portfolio_state.open_orders),
            "subscribed_symbols": list(self.subscribed_symbols),
            "strategies_active": list(self.strategies.keys()),
            "last_update": datetime.utcnow().isoformat()
        }
    
    async def manual_trade(self, symbol: str, side: str, size: float, 
                          order_type: str = "LIMIT", price: Optional[float] = None) -> bool:
        """Execute a manual trade with full validation."""
        try:
            # Validate inputs
            order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
            order_type_enum = OrderType.LIMIT if order_type.upper() == "LIMIT" else OrderType.MARKET
            
            # Get current price if not provided
            if price is None or order_type_enum == OrderType.MARKET:
                if symbol not in self.trading_engine.current_prices:
                    return False
                current_tick = self.trading_engine.current_prices[symbol]
                price = current_tick.ask if order_side == OrderSide.BUY else current_tick.bid
                if price == 0:
                    price = current_tick.price
            
            # Create order
            order = Order(
                id=str(uuid.uuid4()),
                symbol=symbol,
                side=order_side,
                type=order_type_enum,
                size=size,
                price=price,
                ts=datetime.utcnow()
            )
            
            # Submit with full validation
            return await self.trading_engine.submit_order(order)
            
        except Exception as e:
            self.logger.error("Error executing manual trade", error=str(e))
            return False