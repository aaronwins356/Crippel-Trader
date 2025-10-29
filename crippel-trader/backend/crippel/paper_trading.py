"""Paper trading simulation engine with real market data."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

import structlog
from pydantic import BaseModel

from .config import get_settings
from .models.core import (
    Order, Fill, Position, PortfolioState, PriceTick, 
    OrderSide, OrderType, Mode, TradeStat
)
from .notifications import get_notification_service


class PaperTradingEngine:
    """Paper trading simulation engine that executes trades against real market data."""
    
    def __init__(self, initial_capital: float = 200.0):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        self.notification_service = get_notification_service()
        
        # Portfolio state
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.open_orders: Dict[str, Order] = {}
        self.filled_orders: List[Fill] = []
        self.trade_history: List[Fill] = []
        
        # Market data
        self.current_prices: Dict[str, PriceTick] = {}
        self.price_history: Dict[str, List[PriceTick]] = {}
        
        # Performance tracking
        self.equity_history: List[tuple[datetime, float]] = []
        self.max_equity = initial_capital
        self.max_drawdown = 0.0
        self.daily_pnl = 0.0
        self.last_equity_snapshot = initial_capital
        
        # Risk management
        self.current_aggression = self.settings.default_aggression
        self.risk_limits = self._calculate_risk_limits(self.current_aggression)
        
        # Statistics
        self.stats = TradeStat(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            fees_paid=0.0,
            realized_pnl=0.0
        )
        
        self.logger.info("Paper trading engine initialized", initial_capital=initial_capital)
    
    def _calculate_risk_limits(self, aggression: int) -> Dict[str, float]:
        """Calculate risk limits based on aggression level."""
        return {
            "drawdown_limit": self.settings.get_dynamic_drawdown_limit(aggression),
            "per_trade_cap": self.settings.get_dynamic_per_trade_cap(aggression),
            "per_symbol_exposure": self.settings.get_dynamic_per_symbol_exposure(aggression),
            "position_size_multiplier": self.settings.get_position_size_multiplier(aggression)
        }
    
    async def update_market_data(self, tick: PriceTick) -> None:
        """Update market data and check for order fills."""
        self.current_prices[tick.symbol] = tick
        
        # Store price history for analysis
        if tick.symbol not in self.price_history:
            self.price_history[tick.symbol] = []
        
        self.price_history[tick.symbol].append(tick)
        
        # Keep only last 1000 ticks per symbol to manage memory
        if len(self.price_history[tick.symbol]) > 1000:
            self.price_history[tick.symbol] = self.price_history[tick.symbol][-1000:]
        
        # Check for order fills
        await self._check_order_fills(tick)
        
        # Update portfolio state
        await self._update_portfolio_state()
    
    async def submit_order(self, order: Order) -> bool:
        """Submit a paper trading order."""
        try:
            # Validate order
            if not await self._validate_order(order):
                return False
            
            # Add to open orders
            self.open_orders[order.id] = order
            
            self.logger.info("Paper order submitted", order=order)
            
            # Send notification
            await self.notification_service.send_trade_alert(
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.size,
                price=order.price,
                strategy="Paper Trading"
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to submit paper order", order=order, error=str(e))
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        if order_id in self.open_orders:
            order = self.open_orders.pop(order_id)
            self.logger.info("Paper order cancelled", order_id=order_id)
            return True
        return False
    
    async def set_aggression(self, aggression: int) -> None:
        """Update aggression level and recalculate risk limits."""
        if 1 <= aggression <= 10:
            self.current_aggression = aggression
            self.risk_limits = self._calculate_risk_limits(aggression)
            
            self.logger.info("Aggression level updated", aggression=aggression, risk_limits=self.risk_limits)
            
            await self.notification_service.send_system_alert(
                "Aggression Updated",
                f"Risk aggression set to {aggression}/10",
                "info"
            )
    
    async def _validate_order(self, order: Order) -> bool:
        """Validate order against risk limits and available capital."""
        # Check if we have current price data
        if order.symbol not in self.current_prices:
            self.logger.warning("No price data for symbol", symbol=order.symbol)
            return False
        
        current_price = self.current_prices[order.symbol].price
        order_value = order.size * current_price
        
        # Check per-trade capital limit
        max_trade_value = self.get_current_equity() * self.risk_limits["per_trade_cap"]
        if order_value > max_trade_value:
            self.logger.warning(
                "Order exceeds per-trade limit",
                order_value=order_value,
                max_trade_value=max_trade_value
            )
            return False
        
        # Check available cash for buy orders
        if order.side == OrderSide.BUY:
            required_cash = order_value * (1 + self.settings.taker_fee_bps / 10000)
            if required_cash > self.cash:
                self.logger.warning(
                    "Insufficient cash for buy order",
                    required_cash=required_cash,
                    available_cash=self.cash
                )
                return False
        
        # Check position size limits
        current_position = self.positions.get(order.symbol, Position(symbol=order.symbol))
        max_position_value = self.get_current_equity() * self.risk_limits["per_symbol_exposure"]
        
        if order.side == OrderSide.BUY:
            new_position_size = current_position.size + order.size
        else:
            new_position_size = abs(current_position.size - order.size)
        
        new_position_value = new_position_size * current_price
        if new_position_value > max_position_value:
            self.logger.warning(
                "Order would exceed per-symbol exposure limit",
                new_position_value=new_position_value,
                max_position_value=max_position_value
            )
            return False
        
        return True
    
    async def _check_order_fills(self, tick: PriceTick) -> None:
        """Check if any open orders should be filled based on current price."""
        orders_to_fill = []
        
        for order_id, order in self.open_orders.items():
            if order.symbol != tick.symbol:
                continue
            
            should_fill = False
            fill_price = order.price
            
            if order.type == OrderType.MARKET:
                # Market orders fill immediately at current price
                should_fill = True
                fill_price = tick.price
                
            elif order.type == OrderType.LIMIT:
                # Limit orders fill when price crosses the limit
                if order.side == OrderSide.BUY and tick.ask <= order.price:
                    should_fill = True
                    fill_price = min(order.price, tick.ask)
                elif order.side == OrderSide.SELL and tick.bid >= order.price:
                    should_fill = True
                    fill_price = max(order.price, tick.bid)
            
            if should_fill:
                orders_to_fill.append((order_id, order, fill_price))
        
        # Process fills
        for order_id, order, fill_price in orders_to_fill:
            await self._execute_fill(order_id, order, fill_price, tick.ts)
    
    async def _execute_fill(self, order_id: str, order: Order, fill_price: float, ts: datetime) -> None:
        """Execute a fill for an order."""
        # Determine if this is a maker or taker fill
        is_maker = order.type == OrderType.LIMIT
        trade_value = order.size * fill_price
        fee = self.stats.apply_fee(trade_value, is_maker)
        
        # Create fill
        fill = Fill(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            price=fill_price,
            fee=fee,
            ts=ts,
            maker=is_maker
        )
        
        # Update cash
        if order.side == OrderSide.BUY:
            self.cash -= (order.size * fill_price + fee)
        else:
            self.cash += (order.size * fill_price - fee)
        
        # Update position
        if order.symbol not in self.positions:
            self.positions[order.symbol] = Position(symbol=order.symbol)
        
        old_realized_pnl = self.positions[order.symbol].realized_pnl
        self.positions[order.symbol].update_with_fill(fill)
        pnl_change = self.positions[order.symbol].realized_pnl - old_realized_pnl
        
        # Update statistics
        self.stats.record_trade(realized_pnl=pnl_change, is_winning=pnl_change >= 0)
        
        # Store fill
        self.filled_orders.append(fill)
        self.trade_history.append(fill)
        
        # Remove from open orders
        self.open_orders.pop(order_id)
        
        self.logger.info("Order filled", fill=fill, pnl_change=pnl_change)
        
        # Send notification
        await self.notification_service.send_trade_alert(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.size,
            price=fill_price,
            pnl=pnl_change if pnl_change != 0 else None,
            strategy="Paper Trading"
        )
    
    async def _update_portfolio_state(self) -> None:
        """Update portfolio state and check risk limits."""
        current_equity = self.get_current_equity()
        
        # Update equity history
        now = datetime.utcnow()
        self.equity_history.append((now, current_equity))
        
        # Keep only last 24 hours of equity history
        cutoff_time = now - timedelta(hours=24)
        self.equity_history = [
            (ts, equity) for ts, equity in self.equity_history 
            if ts > cutoff_time
        ]
        
        # Update max equity and drawdown
        if current_equity > self.max_equity:
            self.max_equity = current_equity
        
        current_drawdown = (self.max_equity - current_equity) / self.max_equity
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Check drawdown limit
        if current_drawdown > self.risk_limits["drawdown_limit"]:
            await self._handle_drawdown_breach(current_drawdown)
        
        # Update daily P&L
        if len(self.equity_history) > 0:
            start_of_day_equity = next(
                (equity for ts, equity in self.equity_history if ts.date() == now.date()),
                self.initial_capital
            )
            self.daily_pnl = current_equity - start_of_day_equity
    
    async def _handle_drawdown_breach(self, current_drawdown: float) -> None:
        """Handle drawdown limit breach."""
        self.logger.error(
            "Drawdown limit breached",
            current_drawdown=current_drawdown,
            limit=self.risk_limits["drawdown_limit"]
        )
        
        # Cancel all open orders
        order_ids = list(self.open_orders.keys())
        for order_id in order_ids:
            await self.cancel_order(order_id)
        
        # Send risk alert
        await self.notification_service.send_risk_alert(
            alert_type="Drawdown Limit Breach",
            current_value=current_drawdown * 100,
            threshold=self.risk_limits["drawdown_limit"] * 100,
            action_taken="All open orders cancelled"
        )
    
    def get_current_equity(self) -> float:
        """Calculate current total equity."""
        unrealized_pnl = 0.0
        
        for symbol, position in self.positions.items():
            if position.size != 0 and symbol in self.current_prices:
                current_price = self.current_prices[symbol].price
                unrealized_pnl += (current_price - position.average_price) * position.size
        
        return self.cash + unrealized_pnl
    
    def get_portfolio_state(self) -> PortfolioState:
        """Get current portfolio state."""
        unrealized_pnl = 0.0
        
        for symbol, position in self.positions.items():
            if position.size != 0 and symbol in self.current_prices:
                current_price = self.current_prices[symbol].price
                unrealized_pnl += (current_price - position.average_price) * position.size
        
        return PortfolioState(
            cash=self.cash,
            equity=self.get_current_equity(),
            pnl_realized=self.stats.realized_pnl,
            pnl_unrealized=unrealized_pnl,
            positions=self.positions.copy(),
            mode=Mode.PAPER,
            ts=datetime.utcnow()
        )
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for dashboard."""
        current_equity = self.get_current_equity()
        total_return = (current_equity - self.initial_capital) / self.initial_capital * 100
        
        return {
            "initial_capital": self.initial_capital,
            "current_equity": current_equity,
            "cash": self.cash,
            "total_return_pct": total_return,
            "daily_pnl": self.daily_pnl,
            "max_drawdown_pct": self.max_drawdown * 100,
            "total_trades": self.stats.total_trades,
            "win_rate_pct": self.stats.win_rate * 100,
            "fees_paid": self.stats.fees_paid,
            "realized_pnl": self.stats.realized_pnl,
            "aggression_level": self.current_aggression,
            "open_orders": len(self.open_orders),
            "active_positions": len([p for p in self.positions.values() if p.size != 0])
        }
    
    async def send_daily_performance_update(self) -> None:
        """Send daily performance update notification."""
        summary = self.get_performance_summary()
        
        await self.notification_service.send_performance_update(
            total_pnl=summary["realized_pnl"],
            daily_pnl=summary["daily_pnl"],
            win_rate=summary["win_rate_pct"],
            total_trades=summary["total_trades"],
            equity=summary["current_equity"],
            drawdown=summary["max_drawdown_pct"]
        )
    
    def reset(self, new_capital: Optional[float] = None) -> None:
        """Reset the paper trading engine."""
        if new_capital:
            self.initial_capital = new_capital
        
        self.cash = self.initial_capital
        self.positions.clear()
        self.open_orders.clear()
        self.filled_orders.clear()
        self.trade_history.clear()
        self.current_prices.clear()
        self.price_history.clear()
        self.equity_history.clear()
        
        self.max_equity = self.initial_capital
        self.max_drawdown = 0.0
        self.daily_pnl = 0.0
        
        self.stats = TradeStat(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            fees_paid=0.0,
            realized_pnl=0.0
        )
        
        self.logger.info("Paper trading engine reset", initial_capital=self.initial_capital)