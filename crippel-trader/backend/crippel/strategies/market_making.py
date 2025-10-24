"""Market making trading strategies."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

import numpy as np

from .base import BaseStrategy, StrategySignal, SignalType
from ..models.core import PriceTick


class MarketMakingStrategy(BaseStrategy):
    """Basic market making strategy with dynamic spreads."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "base_spread": 0.002,           # 0.2% base spread
            "min_spread": 0.001,            # 0.1% minimum spread
            "max_spread": 0.01,             # 1% maximum spread
            "volatility_multiplier": 2.0,   # Spread adjustment based on volatility
            "inventory_limit": 0.1,         # 10% of portfolio in any symbol
            "quote_refresh_seconds": 30,    # Refresh quotes every 30 seconds
            "min_profit_per_trade": 0.0005, # 0.05% minimum profit per trade
            "max_position_time": 3600,      # Max time to hold inventory (seconds)
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("MarketMaking_Strategy", symbols, default_params)
        
        # Market making state
        self.active_quotes: Dict[str, Dict[str, Any]] = {}
        self.inventory: Dict[str, float] = {symbol: 0.0 for symbol in symbols}
        self.last_quote_time: Dict[str, datetime] = {}
        self.recent_trades: Dict[str, deque] = {symbol: deque(maxlen=100) for symbol in symbols}
        
        # Volatility tracking
        self.volatility_window = 50
        self.price_changes: Dict[str, deque] = {symbol: deque(maxlen=self.volatility_window) for symbol in symbols}
    
    def get_required_history_length(self) -> int:
        return max(self.volatility_window, 20)
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate market making signals."""
        if not self.is_active:
            return None
        
        # Update volatility tracking
        await self._update_volatility(tick)
        
        # Check if we need to refresh quotes
        if await self._should_refresh_quotes(tick):
            return await self._generate_market_making_quote(tick)
        
        # Check for inventory management signals
        return await self._check_inventory_management(tick)
    
    async def _update_volatility(self, tick: PriceTick) -> None:
        """Update volatility estimates for dynamic spread calculation."""
        symbol = tick.symbol
        
        if symbol in self.price_history and len(self.price_history[symbol]) >= 2:
            prev_price = self.price_history[symbol][-2].price
            price_change = (tick.price - prev_price) / prev_price
            self.price_changes[symbol].append(price_change)
    
    async def _should_refresh_quotes(self, tick: PriceTick) -> bool:
        """Determine if quotes should be refreshed."""
        symbol = tick.symbol
        
        # Check time-based refresh
        if symbol not in self.last_quote_time:
            return True
        
        time_since_last = (tick.ts - self.last_quote_time[symbol]).total_seconds()
        if time_since_last >= self.parameters["quote_refresh_seconds"]:
            return True
        
        # Check volatility-based refresh
        if len(self.price_changes[symbol]) >= 5:
            recent_volatility = np.std(list(self.price_changes[symbol])[-5:])
            if recent_volatility > 0.01:  # High volatility threshold
                return True
        
        return False
    
    async def _generate_market_making_quote(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate market making buy/sell quotes."""
        symbol = tick.symbol
        current_price = tick.price
        
        # Calculate dynamic spread based on volatility
        spread = await self._calculate_dynamic_spread(symbol, current_price)
        
        # Calculate bid and ask prices
        half_spread = spread / 2
        bid_price = current_price * (1 - half_spread)
        ask_price = current_price * (1 + half_spread)
        
        # Check inventory constraints
        inventory_adjustment = await self._calculate_inventory_adjustment(symbol)
        
        # Adjust quotes based on inventory
        bid_price *= (1 + inventory_adjustment)
        ask_price *= (1 + inventory_adjustment)
        
        # Determine which side to quote (or both)
        signal_type = await self._determine_quote_side(symbol, inventory_adjustment)
        
        if signal_type == SignalType.HOLD:
            return None
        
        # Calculate signal strength based on expected profit
        expected_profit = half_spread - self.parameters["min_profit_per_trade"]
        strength = min(1.0, max(0.1, expected_profit * 100))
        
        # Higher confidence for market making in stable conditions
        confidence = 0.7
        if len(self.price_changes[symbol]) >= 10:
            recent_volatility = np.std(list(self.price_changes[symbol])[-10:])
            if recent_volatility < 0.005:  # Low volatility
                confidence = 0.9
        
        # Update quote tracking
        self.active_quotes[symbol] = {
            "bid_price": bid_price,
            "ask_price": ask_price,
            "spread": spread,
            "timestamp": tick.ts,
        }
        self.last_quote_time[symbol] = tick.ts
        
        # Use appropriate price based on signal type
        quote_price = bid_price if signal_type == SignalType.BUY else ask_price
        
        return StrategySignal(
            symbol=symbol,
            signal=signal_type,
            strength=strength if signal_type == SignalType.BUY else -strength,
            confidence=confidence,
            price=quote_price,
            timestamp=tick.ts,
            metadata={
                "strategy_type": "market_making",
                "bid_price": bid_price,
                "ask_price": ask_price,
                "spread": spread,
                "inventory": self.inventory[symbol],
                "inventory_adjustment": inventory_adjustment,
                "expected_profit": expected_profit,
            }
        )
    
    async def _calculate_dynamic_spread(self, symbol: str, current_price: float) -> float:
        """Calculate dynamic spread based on market conditions."""
        base_spread = self.parameters["base_spread"]
        
        # Adjust for volatility
        if len(self.price_changes[symbol]) >= 10:
            volatility = np.std(list(self.price_changes[symbol])[-20:])
            volatility_adjustment = volatility * self.parameters["volatility_multiplier"]
            spread = base_spread + volatility_adjustment
        else:
            spread = base_spread
        
        # Adjust for bid-ask spread in market data
        if symbol in self.price_history and self.price_history[symbol]:
            latest_tick = self.price_history[symbol][-1]
            if hasattr(latest_tick, 'bid') and hasattr(latest_tick, 'ask') and latest_tick.bid > 0 and latest_tick.ask > 0:
                market_spread = (latest_tick.ask - latest_tick.bid) / latest_tick.price
                # Use wider of our calculated spread or market spread + buffer
                spread = max(spread, market_spread * 1.2)
        
        # Apply limits
        spread = max(self.parameters["min_spread"], min(self.parameters["max_spread"], spread))
        
        return spread
    
    async def _calculate_inventory_adjustment(self, symbol: str) -> float:
        """Calculate inventory-based price adjustment."""
        current_inventory = self.inventory[symbol]
        inventory_limit = self.parameters["inventory_limit"]
        
        # Normalize inventory to [-1, 1] range
        normalized_inventory = current_inventory / inventory_limit
        normalized_inventory = max(-1.0, min(1.0, normalized_inventory))
        
        # Adjustment factor: positive inventory -> lower bids/asks to sell
        # negative inventory -> higher bids/asks to buy
        adjustment = -normalized_inventory * 0.001  # 0.1% max adjustment
        
        return adjustment
    
    async def _determine_quote_side(self, symbol: str, inventory_adjustment: float) -> SignalType:
        """Determine which side to quote based on inventory and market conditions."""
        current_inventory = self.inventory[symbol]
        inventory_limit = self.parameters["inventory_limit"]
        
        # If inventory is near limits, only quote the side that reduces inventory
        if current_inventory > inventory_limit * 0.8:
            return SignalType.SELL  # Need to sell to reduce inventory
        elif current_inventory < -inventory_limit * 0.8:
            return SignalType.BUY   # Need to buy to reduce short inventory
        
        # Normal market making - alternate between buy and sell
        # For simplicity, use timestamp to alternate
        if int(datetime.utcnow().timestamp()) % 2 == 0:
            return SignalType.BUY
        else:
            return SignalType.SELL
    
    async def _check_inventory_management(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Check if inventory management actions are needed."""
        symbol = tick.symbol
        current_inventory = self.inventory[symbol]
        inventory_limit = self.parameters["inventory_limit"]
        
        # Check for inventory limit breaches
        if abs(current_inventory) > inventory_limit:
            # Emergency inventory reduction
            signal_type = SignalType.SELL if current_inventory > 0 else SignalType.BUY
            strength = min(1.0, abs(current_inventory) / inventory_limit)
            confidence = 0.9  # High confidence for risk management
            
            return StrategySignal(
                symbol=symbol,
                signal=signal_type,
                strength=strength if signal_type == SignalType.BUY else -strength,
                confidence=confidence,
                price=tick.price,
                timestamp=tick.ts,
                metadata={
                    "strategy_type": "inventory_management",
                    "inventory": current_inventory,
                    "inventory_limit": inventory_limit,
                    "action": "emergency_reduction",
                }
            )
        
        # Check for aged inventory
        if symbol in self.active_quotes:
            quote_age = (tick.ts - self.active_quotes[symbol]["timestamp"]).total_seconds()
            if quote_age > self.parameters["max_position_time"] and abs(current_inventory) > 0:
                # Liquidate aged inventory
                signal_type = SignalType.SELL if current_inventory > 0 else SignalType.BUY
                strength = 0.8
                confidence = 0.8
                
                return StrategySignal(
                    symbol=symbol,
                    signal=signal_type,
                    strength=strength if signal_type == SignalType.BUY else -strength,
                    confidence=confidence,
                    price=tick.price,
                    timestamp=tick.ts,
                    metadata={
                        "strategy_type": "inventory_management",
                        "inventory": current_inventory,
                        "quote_age": quote_age,
                        "action": "aged_inventory_liquidation",
                    }
                )
        
        return None
    
    def update_inventory(self, symbol: str, quantity_change: float) -> None:
        """Update inventory after a trade."""
        if symbol in self.inventory:
            self.inventory[symbol] += quantity_change
            self.logger.info("Inventory updated", symbol=symbol, change=quantity_change, new_inventory=self.inventory[symbol])


class AdaptiveMarketMakingStrategy(BaseStrategy):
    """Advanced market making with machine learning-like adaptation."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "learning_rate": 0.01,          # How quickly to adapt
            "profit_target": 0.001,         # 0.1% profit target per trade
            "max_adverse_selection": 0.005, # 0.5% max adverse selection
            "order_flow_window": 100,       # Window for order flow analysis
            "adaptation_period": 1000,      # Trades before major adaptation
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("Adaptive_MarketMaking", symbols, default_params)
        
        # Adaptive parameters
        self.learned_spreads: Dict[str, float] = {symbol: 0.002 for symbol in symbols}
        self.adverse_selection_rate: Dict[str, float] = {symbol: 0.0 for symbol in symbols}
        self.fill_rates: Dict[str, float] = {symbol: 0.5 for symbol in symbols}
        
        # Performance tracking
        self.quote_performance: Dict[str, List[Dict[str, Any]]] = {symbol: [] for symbol in symbols}
    
    def get_required_history_length(self) -> int:
        return 100
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate adaptive market making signals."""
        if not self.is_active:
            return None
        
        # Update learning parameters
        await self._update_learning_parameters(tick)
        
        # Generate adaptive quote
        return await self._generate_adaptive_quote(tick)
    
    async def _update_learning_parameters(self, tick: PriceTick) -> None:
        """Update learning parameters based on recent performance."""
        symbol = tick.symbol
        
        if len(self.quote_performance[symbol]) < 10:
            return
        
        recent_performance = self.quote_performance[symbol][-10:]
        
        # Calculate metrics
        fill_rate = sum(1 for p in recent_performance if p.get("filled", False)) / len(recent_performance)
        avg_adverse_selection = np.mean([p.get("adverse_selection", 0) for p in recent_performance])
        avg_profit = np.mean([p.get("profit", 0) for p in recent_performance])
        
        # Update learned parameters
        learning_rate = self.parameters["learning_rate"]
        
        # Adjust spread based on adverse selection
        if avg_adverse_selection > self.parameters["max_adverse_selection"]:
            # Increase spread to reduce adverse selection
            self.learned_spreads[symbol] *= (1 + learning_rate)
        elif avg_adverse_selection < self.parameters["max_adverse_selection"] * 0.5:
            # Decrease spread to increase fill rate
            self.learned_spreads[symbol] *= (1 - learning_rate * 0.5)
        
        # Update tracking
        self.fill_rates[symbol] = fill_rate
        self.adverse_selection_rate[symbol] = avg_adverse_selection
        
        self.logger.debug(
            "Learning parameters updated",
            symbol=symbol,
            learned_spread=self.learned_spreads[symbol],
            fill_rate=fill_rate,
            adverse_selection=avg_adverse_selection
        )
    
    async def _generate_adaptive_quote(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate quote using learned parameters."""
        symbol = tick.symbol
        current_price = tick.price
        
        # Use learned spread
        spread = self.learned_spreads[symbol]
        
        # Adjust for current market conditions
        if len(self.price_changes[symbol]) >= 5:
            recent_volatility = np.std(list(self.price_changes[symbol])[-5:])
            volatility_adjustment = recent_volatility * 0.5
            spread += volatility_adjustment
        
        # Calculate quote prices
        half_spread = spread / 2
        bid_price = current_price * (1 - half_spread)
        ask_price = current_price * (1 + half_spread)
        
        # Determine quote side based on recent fill rates
        fill_rate = self.fill_rates[symbol]
        
        if fill_rate < 0.3:  # Low fill rate, be more aggressive
            signal_type = SignalType.BUY if np.random.random() > 0.5 else SignalType.SELL
            strength = 0.8
        elif fill_rate > 0.7:  # High fill rate, be more selective
            signal_type = SignalType.BUY if np.random.random() > 0.7 else SignalType.SELL
            strength = 0.4
        else:  # Normal fill rate
            signal_type = SignalType.BUY if np.random.random() > 0.5 else SignalType.SELL
            strength = 0.6
        
        confidence = min(0.9, 0.5 + fill_rate * 0.4)  # Higher confidence with good fill rates
        
        quote_price = bid_price if signal_type == SignalType.BUY else ask_price
        
        # Record quote for learning
        quote_record = {
            "timestamp": tick.ts,
            "bid_price": bid_price,
            "ask_price": ask_price,
            "spread": spread,
            "signal_type": signal_type,
            "filled": False,  # Will be updated when trade executes
            "adverse_selection": 0.0,  # Will be calculated later
            "profit": 0.0,  # Will be calculated later
        }
        
        self.quote_performance[symbol].append(quote_record)
        
        # Keep only recent performance data
        if len(self.quote_performance[symbol]) > self.parameters["adaptation_period"]:
            self.quote_performance[symbol] = self.quote_performance[symbol][-self.parameters["adaptation_period"]:]
        
        return StrategySignal(
            symbol=symbol,
            signal=signal_type,
            strength=strength if signal_type == SignalType.BUY else -strength,
            confidence=confidence,
            price=quote_price,
            timestamp=tick.ts,
            metadata={
                "strategy_type": "adaptive_market_making",
                "learned_spread": spread,
                "fill_rate": fill_rate,
                "adverse_selection_rate": self.adverse_selection_rate[symbol],
                "bid_price": bid_price,
                "ask_price": ask_price,
            }
        )
    
    def record_trade_outcome(self, symbol: str, filled: bool, profit: float, adverse_selection: float) -> None:
        """Record the outcome of a trade for learning."""
        if symbol in self.quote_performance and self.quote_performance[symbol]:
            # Update the most recent quote
            self.quote_performance[symbol][-1].update({
                "filled": filled,
                "profit": profit,
                "adverse_selection": adverse_selection,
            })
            
            self.logger.debug(
                "Trade outcome recorded",
                symbol=symbol,
                filled=filled,
                profit=profit,
                adverse_selection=adverse_selection
            )