"""Real trading engine with live market data and proper capital management."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN
import pytz

import structlog
from pydantic import BaseModel

from .config import get_settings
from .models.core import (
    Order, Fill, Position, PortfolioState, PriceTick, 
    OrderSide, OrderType, Mode, TradeStat
)
from .notifications import get_notification_service


@dataclass
class MarketHours:
    """Market hours configuration for different asset types."""
    crypto_24_7: bool = True
    stock_market_open: time = time(9, 30)  # 9:30 AM EST
    stock_market_close: time = time(16, 0)  # 4:00 PM EST
    stock_timezone: str = "US/Eastern"


@dataclass
class TradingFees:
    """Real trading fees structure."""
    crypto_maker_bps: float = 16.0  # 0.16% Kraken maker fee
    crypto_taker_bps: float = 26.0  # 0.26% Kraken taker fee
    stock_maker_bps: float = 0.0    # No maker fees for stocks
    stock_taker_bps: float = 0.0    # Commission-free stock trading
    min_fee_usd: float = 0.01       # Minimum fee


@dataclass
class SlippageModel:
    """Realistic slippage model based on order size and market conditions."""
    base_slippage_bps: float = 2.0  # Base 0.02% slippage
    size_impact_factor: float = 0.1  # Additional slippage per $1000 order size
    volatility_multiplier: float = 1.5  # Multiply slippage during high volatility


class RealTradingEngine:
    """Real trading engine with live market data and proper capital management."""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        self.notification_service = get_notification_service()
        
        # Portfolio state - REAL money tracking
        self.initial_capital = Decimal(str(initial_capital))
        self.cash = Decimal(str(initial_capital))
        self.positions: Dict[str, Position] = {}
        self.open_orders: Dict[str, Order] = {}
        self.filled_orders: List[Fill] = []
        self.trade_history: List[Fill] = []
        
        # Market data - LIVE prices only
        self.current_prices: Dict[str, PriceTick] = {}
        self.price_history: Dict[str, List[PriceTick]] = {}
        self.bid_ask_spreads: Dict[str, Tuple[float, float]] = {}  # (bid, ask)
        
        # Market configuration
        self.market_hours = MarketHours()
        self.trading_fees = TradingFees()
        self.slippage_model = SlippageModel()
        
        # Performance tracking
        self.equity_history: List[tuple[datetime, float]] = []
        self.max_equity = float(initial_capital)
        self.max_drawdown = 0.0
        self.daily_pnl = 0.0
        
        # Risk management - STRICT capital controls
        self.max_position_size_pct = 0.20  # Max 20% of capital per position
        self.max_total_exposure_pct = 0.80  # Max 80% of capital deployed
        self.min_cash_reserve_pct = 0.10   # Keep 10% cash reserve
        self.max_daily_loss_pct = 0.05     # Max 5% daily loss
        
        # Trading statistics
        self.stats = TradeStat()
        
        self.logger.info("Real trading engine initialized", 
                        initial_capital=initial_capital,
                        max_position_size=f"{self.max_position_size_pct*100}%",
                        cash_reserve=f"{self.min_cash_reserve_pct*100}%")
    
    def get_available_cash(self) -> float:
        """Get available cash for trading (excluding reserves)."""
        total_equity = self.get_current_equity()
        min_reserve = total_equity * self.min_cash_reserve_pct
        return max(0.0, float(self.cash) - min_reserve)
    
    def get_current_equity(self) -> float:
        """Calculate current total equity (cash + positions)."""
        equity = float(self.cash)
        
        for symbol, position in self.positions.items():
            if symbol in self.current_prices and position.size != 0:
                current_price = self.current_prices[symbol].price
                position_value = position.size * current_price
                equity += position_value
        
        return equity
    
    def get_position_value(self, symbol: str) -> float:
        """Get current value of a position."""
        if symbol not in self.positions or symbol not in self.current_prices:
            return 0.0
        
        position = self.positions[symbol]
        current_price = self.current_prices[symbol].price
        return position.size * current_price
    
    def get_total_exposure(self) -> float:
        """Get total exposure across all positions."""
        total_exposure = 0.0
        for symbol in self.positions:
            total_exposure += abs(self.get_position_value(symbol))
        return total_exposure
    
    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for trading this symbol."""
        # Crypto markets are always open
        if any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'ADA', 'SOL', 'MATIC']):
            return True
        
        # Stock market hours check
        est = pytz.timezone(self.market_hours.stock_timezone)
        now_est = datetime.now(est).time()
        
        # Check if it's a weekday
        weekday = datetime.now(est).weekday()
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        return (self.market_hours.stock_market_open <= now_est <= 
                self.market_hours.stock_market_close)
    
    def calculate_realistic_slippage(self, symbol: str, order_value: float, 
                                   side: OrderSide) -> float:
        """Calculate realistic slippage based on order size and market conditions."""
        base_slippage = self.slippage_model.base_slippage_bps / 10000
        
        # Size impact - larger orders have more slippage
        size_impact = (order_value / 1000) * (self.slippage_model.size_impact_factor / 10000)
        
        # Volatility impact (simplified - could be enhanced with real volatility data)
        volatility_impact = 0.0
        if symbol in self.price_history and len(self.price_history[symbol]) > 10:
            recent_prices = [tick.price for tick in self.price_history[symbol][-10:]]
            price_std = Decimal(str(sum(recent_prices))) / len(recent_prices)
            volatility_impact = float(price_std) * 0.001  # Simplified volatility measure
        
        total_slippage = base_slippage + size_impact + volatility_impact
        return min(total_slippage, 0.01)  # Cap at 1% slippage
    
    def calculate_trading_fees(self, symbol: str, order_value: float, is_maker: bool) -> float:
        """Calculate realistic trading fees."""
        # Determine if crypto or stock
        is_crypto = any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'ADA', 'SOL', 'MATIC'])
        
        if is_crypto:
            fee_bps = self.trading_fees.crypto_maker_bps if is_maker else self.trading_fees.crypto_taker_bps
        else:
            fee_bps = self.trading_fees.stock_maker_bps if is_maker else self.trading_fees.stock_taker_bps
        
        fee = order_value * (fee_bps / 10000)
        return max(fee, self.trading_fees.min_fee_usd)
    
    def get_realistic_execution_price(self, symbol: str, side: OrderSide, 
                                    order_type: OrderType, limit_price: Optional[float] = None) -> float:
        """Get realistic execution price including bid/ask spread and slippage."""
        if symbol not in self.current_prices:
            raise ValueError(f"No price data available for {symbol}")
        
        tick = self.current_prices[symbol]
        
        if order_type == OrderType.MARKET:
            # Market orders execute at bid/ask with slippage
            if side == OrderSide.BUY:
                base_price = tick.ask if hasattr(tick, 'ask') and tick.ask else tick.price
            else:
                base_price = tick.bid if hasattr(tick, 'bid') and tick.bid else tick.price
            
            # Add slippage
            order_value = base_price * 100  # Estimate for slippage calculation
            slippage = self.calculate_realistic_slippage(symbol, order_value, side)
            
            if side == OrderSide.BUY:
                return base_price * (1 + slippage)
            else:
                return base_price * (1 - slippage)
        
        elif order_type == OrderType.LIMIT:
            # Limit orders execute at limit price or better
            return limit_price
        
        return tick.price
    
    async def validate_order_capital(self, order: Order) -> Tuple[bool, str]:
        """Strict validation of order against available capital."""
        # Check if market is open
        if not self.is_market_open(order.symbol):
            return False, f"Market closed for {order.symbol}"
        
        # Check if we have current price data
        if order.symbol not in self.current_prices:
            return False, f"No live price data for {order.symbol}"
        
        # Get realistic execution price
        try:
            execution_price = self.get_realistic_execution_price(
                order.symbol, order.side, order.type, order.price
            )
        except ValueError as e:
            return False, str(e)
        
        order_value = Decimal(str(order.size)) * Decimal(str(execution_price))
        
        # Calculate fees
        is_maker = order.type == OrderType.LIMIT
        fees = Decimal(str(self.calculate_trading_fees(order.symbol, float(order_value), is_maker)))
        
        if order.side == OrderSide.BUY:
            # Check available cash (including fees)
            total_cost = order_value + fees
            available_cash = Decimal(str(self.get_available_cash()))
            
            if total_cost > available_cash:
                return False, f"Insufficient funds: need ${total_cost:.2f}, have ${available_cash:.2f}"
            
            # Check position size limits
            current_equity = Decimal(str(self.get_current_equity()))
            max_position_value = current_equity * Decimal(str(self.max_position_size_pct))
            
            current_position_value = Decimal(str(self.get_position_value(order.symbol)))
            new_position_value = current_position_value + order_value
            
            if new_position_value > max_position_value:
                return False, f"Position size limit: max ${max_position_value:.2f}, would be ${new_position_value:.2f}"
        
        else:  # SELL order
            # Check if we have enough shares to sell
            current_position = self.positions.get(order.symbol, Position(symbol=order.symbol))
            if current_position.size < order.size:
                return False, f"Insufficient shares: have {current_position.size}, trying to sell {order.size}"
        
        # Check total exposure limits
        current_exposure = Decimal(str(self.get_total_exposure()))
        max_exposure = Decimal(str(self.get_current_equity())) * Decimal(str(self.max_total_exposure_pct))
        
        if order.side == OrderSide.BUY and current_exposure + order_value > max_exposure:
            return False, f"Total exposure limit: max ${max_exposure:.2f}, would be ${current_exposure + order_value:.2f}"
        
        # Check daily loss limits
        daily_pnl_pct = self.daily_pnl / float(self.initial_capital)
        if daily_pnl_pct < -self.max_daily_loss_pct:
            return False, f"Daily loss limit reached: {daily_pnl_pct*100:.1f}%"
        
        return True, "Order validated"
    
    async def submit_order(self, order: Order) -> bool:
        """Submit order with strict capital validation."""
        # Validate order
        is_valid, message = await self.validate_order_capital(order)
        if not is_valid:
            self.logger.warning("Order rejected", reason=message, order=order)
            await self.notification_service.send_system_alert(
                "Order Rejected", message, "warning"
            )
            return False
        
        # Add to open orders
        self.open_orders[order.id] = order
        
        self.logger.info("Real order submitted", order=order, validation=message)
        
        # Send notification
        await self.notification_service.send_trade_alert(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.size,
            price=order.price,
            strategy="Real Trading"
        )
        
        return True
    
    async def update_market_data(self, tick: PriceTick) -> None:
        """Update market data and check for order fills."""
        # Store current price
        self.current_prices[tick.symbol] = tick
        
        # Store price history (keep last 1000 ticks per symbol)
        if tick.symbol not in self.price_history:
            self.price_history[tick.symbol] = []
        
        self.price_history[tick.symbol].append(tick)
        if len(self.price_history[tick.symbol]) > 1000:
            self.price_history[tick.symbol] = self.price_history[tick.symbol][-1000:]
        
        # Store bid/ask if available
        if hasattr(tick, 'bid') and hasattr(tick, 'ask'):
            self.bid_ask_spreads[tick.symbol] = (tick.bid, tick.ask)
        
        # Check for order fills
        await self._check_realistic_fills(tick)
        
        # Update portfolio state
        await self._update_portfolio_state()
    
    async def _check_realistic_fills(self, tick: PriceTick) -> None:
        """Check for order fills with realistic execution logic."""
        orders_to_fill = []
        
        for order_id, order in self.open_orders.items():
            if order.symbol != tick.symbol:
                continue
            
            should_fill = False
            fill_price = order.price
            
            if order.type == OrderType.MARKET:
                # Market orders fill immediately at realistic price
                should_fill = True
                fill_price = self.get_realistic_execution_price(
                    order.symbol, order.side, order.type
                )
                
            elif order.type == OrderType.LIMIT:
                # Limit orders fill when price crosses limit with realistic bid/ask
                if order.side == OrderSide.BUY:
                    ask_price = tick.ask if hasattr(tick, 'ask') and tick.ask else tick.price
                    if ask_price <= order.price:
                        should_fill = True
                        fill_price = min(order.price, ask_price)
                else:  # SELL
                    bid_price = tick.bid if hasattr(tick, 'bid') and tick.bid else tick.price
                    if bid_price >= order.price:
                        should_fill = True
                        fill_price = max(order.price, bid_price)
            
            if should_fill:
                orders_to_fill.append((order_id, order, fill_price))
        
        # Process fills
        for order_id, order, fill_price in orders_to_fill:
            await self._execute_realistic_fill(order_id, order, fill_price, tick.ts)
    
    async def _execute_realistic_fill(self, order_id: str, order: Order, 
                                    fill_price: float, ts: datetime) -> None:
        """Execute a fill with realistic fees and slippage."""
        # Calculate realistic fees
        is_maker = order.type == OrderType.LIMIT
        order_value = order.size * fill_price
        fee = self.calculate_trading_fees(order.symbol, order_value, is_maker)
        
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
        
        # Update cash with EXACT amounts
        if order.side == OrderSide.BUY:
            total_cost = Decimal(str(order.size * fill_price + fee))
            self.cash -= total_cost
        else:
            total_proceeds = Decimal(str(order.size * fill_price - fee))
            self.cash += total_proceeds
        
        # Update position
        if order.symbol not in self.positions:
            self.positions[order.symbol] = Position(symbol=order.symbol)
        
        old_realized_pnl = self.positions[order.symbol].realized_pnl
        self.positions[order.symbol].update_with_fill(fill)
        pnl_change = self.positions[order.symbol].realized_pnl - old_realized_pnl
        
        # Update statistics
        self.stats.total_trades += 1
        self.stats.fees_paid += fee
        self.stats.realized_pnl += pnl_change
        
        if pnl_change > 0:
            self.stats.winning_trades += 1
        elif pnl_change < 0:
            self.stats.losing_trades += 1
        
        # Store fill
        self.filled_orders.append(fill)
        self.trade_history.append(fill)
        
        # Remove from open orders
        self.open_orders.pop(order_id)
        
        self.logger.info("Realistic order filled", 
                        fill=fill, 
                        pnl_change=pnl_change,
                        remaining_cash=float(self.cash),
                        total_equity=self.get_current_equity())
        
        # Send notification
        await self.notification_service.send_trade_alert(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.size,
            price=fill_price,
            pnl=pnl_change if pnl_change != 0 else None,
            strategy="Real Trading"
        )
    
    async def _update_portfolio_state(self) -> None:
        """Update portfolio state and risk monitoring."""
        current_equity = self.get_current_equity()
        
        # Update equity history
        now = datetime.utcnow()
        self.equity_history.append((now, current_equity))
        
        # Calculate daily P&L
        if len(self.equity_history) > 1:
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_start_equity = None
            
            for ts, equity in reversed(self.equity_history):
                if ts <= start_of_day:
                    day_start_equity = equity
                    break
            
            if day_start_equity:
                self.daily_pnl = current_equity - day_start_equity
        
        # Update max equity and drawdown
        if current_equity > self.max_equity:
            self.max_equity = current_equity
        
        drawdown = (self.max_equity - current_equity) / self.max_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        # Risk monitoring alerts
        if drawdown > 0.10:  # 10% drawdown alert
            await self.notification_service.send_system_alert(
                "High Drawdown Alert",
                f"Current drawdown: {drawdown*100:.1f}%",
                "warning"
            )
        
        if self.daily_pnl / float(self.initial_capital) < -0.03:  # 3% daily loss warning
            await self.notification_service.send_system_alert(
                "Daily Loss Warning",
                f"Daily P&L: ${self.daily_pnl:.2f} ({self.daily_pnl/float(self.initial_capital)*100:.1f}%)",
                "warning"
            )
    
    def get_portfolio_state(self) -> PortfolioState:
        """Get current portfolio state."""
        return PortfolioState(
            cash=float(self.cash),
            equity=self.get_current_equity(),
            positions=list(self.positions.values()),
            open_orders=list(self.open_orders.values()),
            daily_pnl=self.daily_pnl,
            total_pnl=self.get_current_equity() - float(self.initial_capital),
            max_drawdown=self.max_drawdown,
            stats=self.stats
        )