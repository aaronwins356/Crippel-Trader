"""Arbitrage trading strategies."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

import numpy as np

from .base import BaseStrategy, StrategySignal, SignalType
from ..models.core import PriceTick


class ArbitrageStrategy(BaseStrategy):
    """Statistical arbitrage strategy looking for price discrepancies."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "correlation_threshold": 0.7,  # Minimum correlation for pair trading
            "zscore_entry": 2.0,           # Z-score threshold for entry
            "zscore_exit": 0.5,            # Z-score threshold for exit
            "lookback_period": 50,         # Period for calculating statistics
            "min_spread": 0.001,           # Minimum spread to avoid noise
            "max_holding_period": 3600,    # Max holding period in seconds
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("Arbitrage_Strategy", symbols, default_params)
        
        # Track price relationships
        self.price_ratios: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self.correlations: Dict[Tuple[str, str], float] = {}
        self.active_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
        
        # Generate all possible pairs
        self.symbol_pairs = []
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                self.symbol_pairs.append((symbol1, symbol2))
    
    def get_required_history_length(self) -> int:
        return self.parameters["lookback_period"] + 10
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate arbitrage signals based on price relationships."""
        if not self.is_active:
            return None
        
        # Update price relationships for all pairs involving this symbol
        await self._update_price_relationships(tick)
        
        # Look for arbitrage opportunities
        for pair in self.symbol_pairs:
            if tick.symbol in pair:
                signal = await self._check_pair_arbitrage(pair, tick)
                if signal:
                    return signal
        
        return None
    
    async def _update_price_relationships(self, tick: PriceTick) -> None:
        """Update price relationships and correlations."""
        current_prices = {}
        
        # Get current prices for all symbols
        for symbol in self.symbols:
            if symbol in self.price_history and self.price_history[symbol]:
                current_prices[symbol] = self.price_history[symbol][-1].price
        
        # Update price ratios for pairs involving the updated symbol
        for pair in self.symbol_pairs:
            symbol1, symbol2 = pair
            
            if tick.symbol in pair and symbol1 in current_prices and symbol2 in current_prices:
                price1 = current_prices[symbol1]
                price2 = current_prices[symbol2]
                
                if price2 > 0:  # Avoid division by zero
                    ratio = price1 / price2
                    self.price_ratios[pair].append(ratio)
                    
                    # Keep only recent ratios
                    max_ratios = self.parameters["lookback_period"]
                    if len(self.price_ratios[pair]) > max_ratios:
                        self.price_ratios[pair] = self.price_ratios[pair][-max_ratios:]
                    
                    # Update correlation if we have enough data
                    if len(self.price_ratios[pair]) >= 20:
                        await self._update_correlation(pair)
    
    async def _update_correlation(self, pair: Tuple[str, str]) -> None:
        """Update correlation between a pair of symbols."""
        symbol1, symbol2 = pair
        
        # Get price histories
        history1 = self.get_price_history(symbol1, self.parameters["lookback_period"])
        history2 = self.get_price_history(symbol2, self.parameters["lookback_period"])
        
        if len(history1) < 20 or len(history2) < 20:
            return
        
        # Align the histories by timestamp (simplified - assumes same length)
        min_length = min(len(history1), len(history2))
        prices1 = [t.price for t in history1[-min_length:]]
        prices2 = [t.price for t in history2[-min_length:]]
        
        # Calculate returns
        returns1 = [(prices1[i] - prices1[i-1]) / prices1[i-1] for i in range(1, len(prices1))]
        returns2 = [(prices2[i] - prices2[i-1]) / prices2[i-1] for i in range(1, len(prices2))]
        
        if len(returns1) >= 10 and len(returns2) >= 10:
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            if not np.isnan(correlation):
                self.correlations[pair] = correlation
    
    async def _check_pair_arbitrage(self, pair: Tuple[str, str], tick: PriceTick) -> Optional[StrategySignal]:
        """Check for arbitrage opportunities in a symbol pair."""
        symbol1, symbol2 = pair
        
        # Check if we have enough data and correlation
        if (pair not in self.price_ratios or 
            len(self.price_ratios[pair]) < self.parameters["lookback_period"] or
            pair not in self.correlations or
            abs(self.correlations[pair]) < self.parameters["correlation_threshold"]):
            return None
        
        ratios = self.price_ratios[pair]
        current_ratio = ratios[-1]
        
        # Calculate z-score of current ratio
        mean_ratio = np.mean(ratios)
        std_ratio = np.std(ratios)
        
        if std_ratio == 0:
            return None
        
        zscore = (current_ratio - mean_ratio) / std_ratio
        
        # Check for entry signals
        signal_type = SignalType.HOLD
        strength = 0.0
        confidence = 0.0
        target_symbol = tick.symbol
        
        # Positive correlation pair trading
        if self.correlations[pair] > 0:
            if zscore > self.parameters["zscore_entry"]:
                # Ratio is high - sell symbol1, buy symbol2
                if tick.symbol == symbol1:
                    signal_type = SignalType.SELL
                elif tick.symbol == symbol2:
                    signal_type = SignalType.BUY
                
                strength = min(1.0, abs(zscore) / 5.0)
                confidence = min(0.9, abs(self.correlations[pair]))
                
            elif zscore < -self.parameters["zscore_entry"]:
                # Ratio is low - buy symbol1, sell symbol2
                if tick.symbol == symbol1:
                    signal_type = SignalType.BUY
                elif tick.symbol == symbol2:
                    signal_type = SignalType.SELL
                
                strength = min(1.0, abs(zscore) / 5.0)
                confidence = min(0.9, abs(self.correlations[pair]))
        
        # Negative correlation pair trading
        else:
            if zscore > self.parameters["zscore_entry"]:
                # Both should move in same direction for negative correlation
                if tick.symbol == symbol1:
                    signal_type = SignalType.SELL
                elif tick.symbol == symbol2:
                    signal_type = SignalType.SELL
                
                strength = min(1.0, abs(zscore) / 5.0)
                confidence = min(0.9, abs(self.correlations[pair]))
                
            elif zscore < -self.parameters["zscore_entry"]:
                if tick.symbol == symbol1:
                    signal_type = SignalType.BUY
                elif tick.symbol == symbol2:
                    signal_type = SignalType.BUY
                
                strength = min(1.0, abs(zscore) / 5.0)
                confidence = min(0.9, abs(self.correlations[pair]))
        
        # Check exit signals for active positions
        if pair in self.active_pairs:
            if abs(zscore) < self.parameters["zscore_exit"]:
                # Close position
                active_position = self.active_pairs[pair]
                if active_position["symbol"] == tick.symbol:
                    signal_type = SignalType.CLOSE
                    strength = 0.8
                    confidence = 0.9
                    
                    # Remove from active pairs
                    del self.active_pairs[pair]
        
        # Check minimum spread requirement
        if signal_type != SignalType.HOLD and signal_type != SignalType.CLOSE:
            spread = abs(zscore) * std_ratio / mean_ratio
            if spread < self.parameters["min_spread"]:
                return None
            
            # Add to active pairs
            self.active_pairs[pair] = {
                "symbol": tick.symbol,
                "entry_time": tick.ts,
                "entry_zscore": zscore,
                "signal_type": signal_type,
            }
        
        if signal_type == SignalType.HOLD:
            return None
        
        return StrategySignal(
            symbol=tick.symbol,
            signal=signal_type,
            strength=strength if signal_type in [SignalType.BUY, SignalType.CLOSE] else -strength,
            confidence=confidence,
            price=tick.price,
            timestamp=tick.ts,
            metadata={
                "pair": f"{symbol1}/{symbol2}",
                "zscore": zscore,
                "correlation": self.correlations[pair],
                "mean_ratio": mean_ratio,
                "current_ratio": current_ratio,
                "spread": abs(zscore) * std_ratio / mean_ratio,
                "pair_type": "positive_corr" if self.correlations[pair] > 0 else "negative_corr",
            }
        )


class CrossExchangeArbitrageStrategy(BaseStrategy):
    """Cross-exchange arbitrage strategy (simulated for single exchange)."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "min_profit_threshold": 0.005,  # 0.5% minimum profit
            "max_execution_time": 30,       # Max execution time in seconds
            "transaction_cost": 0.002,      # 0.2% transaction cost
            "price_staleness_threshold": 5, # Max price age in seconds
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("CrossExchange_Arbitrage", symbols, default_params)
        
        # Simulate multiple exchange prices by adding noise
        self.exchange_prices: Dict[str, Dict[str, Tuple[float, datetime]]] = defaultdict(dict)
        self.exchange_names = ["Exchange_A", "Exchange_B", "Exchange_C"]
    
    def get_required_history_length(self) -> int:
        return 10  # Minimal history needed
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate cross-exchange arbitrage signals."""
        if not self.is_active:
            return None
        
        # Simulate prices on different exchanges
        await self._simulate_exchange_prices(tick)
        
        # Look for arbitrage opportunities
        return await self._find_arbitrage_opportunity(tick)
    
    async def _simulate_exchange_prices(self, tick: PriceTick) -> None:
        """Simulate prices on different exchanges with realistic spreads."""
        base_price = tick.price
        
        for exchange in self.exchange_names:
            # Add realistic price variations (0.1% to 0.5%)
            if exchange == "Exchange_A":
                # Slightly higher prices (premium exchange)
                price_variation = np.random.normal(0.002, 0.001)
            elif exchange == "Exchange_B":
                # Market prices
                price_variation = np.random.normal(0.0, 0.0015)
            else:  # Exchange_C
                # Slightly lower prices (discount exchange)
                price_variation = np.random.normal(-0.002, 0.001)
            
            simulated_price = base_price * (1 + price_variation)
            self.exchange_prices[tick.symbol][exchange] = (simulated_price, tick.ts)
    
    async def _find_arbitrage_opportunity(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Find arbitrage opportunities across simulated exchanges."""
        if tick.symbol not in self.exchange_prices:
            return None
        
        exchange_data = self.exchange_prices[tick.symbol]
        
        # Filter out stale prices
        current_time = tick.ts
        fresh_prices = {}
        
        for exchange, (price, timestamp) in exchange_data.items():
            age = (current_time - timestamp).total_seconds()
            if age <= self.parameters["price_staleness_threshold"]:
                fresh_prices[exchange] = price
        
        if len(fresh_prices) < 2:
            return None
        
        # Find highest and lowest prices
        max_price = max(fresh_prices.values())
        min_price = min(fresh_prices.values())
        max_exchange = [ex for ex, price in fresh_prices.items() if price == max_price][0]
        min_exchange = [ex for ex, price in fresh_prices.items() if price == min_price][0]
        
        # Calculate potential profit
        price_diff = max_price - min_price
        profit_pct = price_diff / min_price
        
        # Account for transaction costs
        net_profit_pct = profit_pct - (2 * self.parameters["transaction_cost"])
        
        if net_profit_pct > self.parameters["min_profit_threshold"]:
            # Arbitrage opportunity found
            # Buy on low-price exchange, sell on high-price exchange
            # For simulation, we'll generate a buy signal
            
            strength = min(1.0, net_profit_pct * 20)  # Scale profit to strength
            confidence = 0.9  # High confidence for arbitrage
            
            return StrategySignal(
                symbol=tick.symbol,
                signal=SignalType.BUY,  # Simplified - buy low, sell high
                strength=strength,
                confidence=confidence,
                price=min_price,  # Use the lower price for entry
                timestamp=tick.ts,
                metadata={
                    "arbitrage_type": "cross_exchange",
                    "buy_exchange": min_exchange,
                    "sell_exchange": max_exchange,
                    "buy_price": min_price,
                    "sell_price": max_price,
                    "gross_profit_pct": profit_pct,
                    "net_profit_pct": net_profit_pct,
                    "price_difference": price_diff,
                }
            )
        
        return None


class TriangularArbitrageStrategy(BaseStrategy):
    """Triangular arbitrage strategy for currency/crypto triplets."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "min_profit_threshold": 0.003,  # 0.3% minimum profit
            "max_slippage": 0.001,          # 0.1% max slippage
            "execution_speed_bonus": 0.8,   # Confidence bonus for fast execution
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("Triangular_Arbitrage", symbols, default_params)
        
        # Define currency triplets (simplified for crypto)
        self.triplets = self._generate_triplets(symbols)
    
    def _generate_triplets(self, symbols: List[str]) -> List[Tuple[str, str, str]]:
        """Generate valid triangular arbitrage triplets."""
        triplets = []
        
        # Look for USD-based triplets
        usd_pairs = [s for s in symbols if "USD" in s]
        
        for i, pair1 in enumerate(usd_pairs):
            for pair2 in usd_pairs[i+1:]:
                # Extract base currencies
                base1 = pair1.replace("/USD", "").replace("USD", "")
                base2 = pair2.replace("/USD", "").replace("USD", "")
                
                # Look for cross pair
                cross_pair = f"{base1}/{base2}"
                reverse_cross = f"{base2}/{base1}"
                
                if cross_pair in symbols or reverse_cross in symbols:
                    triplets.append((pair1, pair2, cross_pair if cross_pair in symbols else reverse_cross))
        
        return triplets
    
    def get_required_history_length(self) -> int:
        return 5  # Minimal history for arbitrage
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate triangular arbitrage signals."""
        if not self.is_active:
            return None
        
        # Check all triplets involving the updated symbol
        for triplet in self.triplets:
            if tick.symbol in triplet:
                signal = await self._check_triangular_arbitrage(triplet, tick)
                if signal:
                    return signal
        
        return None
    
    async def _check_triangular_arbitrage(self, triplet: Tuple[str, str, str], tick: PriceTick) -> Optional[StrategySignal]:
        """Check for triangular arbitrage opportunity."""
        pair1, pair2, cross_pair = triplet
        
        # Get current prices for all three pairs
        prices = {}
        for pair in triplet:
            if pair in self.price_history and self.price_history[pair]:
                prices[pair] = self.price_history[pair][-1].price
        
        if len(prices) != 3:
            return None  # Don't have all required prices
        
        # Calculate implied cross rate and compare with actual
        # This is a simplified calculation
        price1 = prices[pair1]  # e.g., BTC/USD
        price2 = prices[pair2]  # e.g., ETH/USD
        cross_price = prices[cross_pair]  # e.g., BTC/ETH
        
        # Calculate implied cross rate
        if "USD" in pair1 and "USD" in pair2:
            # Both are USD pairs
            implied_cross = price1 / price2  # BTC/USD ÷ ETH/USD = BTC/ETH
        else:
            return None  # More complex calculation needed
        
        # Compare with actual cross rate
        price_discrepancy = abs(implied_cross - cross_price) / cross_price
        
        if price_discrepancy > self.parameters["min_profit_threshold"]:
            # Arbitrage opportunity found
            
            # Determine direction
            if implied_cross > cross_price:
                # Cross pair is undervalued
                signal_type = SignalType.BUY if tick.symbol == cross_pair else SignalType.SELL
            else:
                # Cross pair is overvalued
                signal_type = SignalType.SELL if tick.symbol == cross_pair else SignalType.BUY
            
            strength = min(1.0, price_discrepancy * 50)
            confidence = 0.85 + self.parameters["execution_speed_bonus"] * 0.1
            
            return StrategySignal(
                symbol=tick.symbol,
                signal=signal_type,
                strength=strength if signal_type == SignalType.BUY else -strength,
                confidence=confidence,
                price=tick.price,
                timestamp=tick.ts,
                metadata={
                    "arbitrage_type": "triangular",
                    "triplet": triplet,
                    "implied_cross_rate": implied_cross,
                    "actual_cross_rate": cross_price,
                    "price_discrepancy": price_discrepancy,
                    "profit_opportunity": price_discrepancy - self.parameters["max_slippage"],
                }
            )
        
        return None