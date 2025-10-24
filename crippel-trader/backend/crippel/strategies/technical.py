"""Technical analysis trading strategies."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any

import numpy as np

from .base import BaseStrategy, StrategySignal, SignalType
from ..models.core import PriceTick


class RSIStrategy(BaseStrategy):
    """RSI-based mean reversion strategy."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "min_strength": 0.3,
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("RSI_Strategy", symbols, default_params)
    
    def get_required_history_length(self) -> int:
        return self.parameters["rsi_period"] + 10
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate RSI-based signals."""
        if not self.is_active:
            return None
        
        indicators = self.get_current_indicators(tick.symbol)
        rsi = indicators.get("rsi_14")
        
        if rsi is None:
            return None
        
        signal_type = SignalType.HOLD
        strength = 0.0
        confidence = 0.0
        
        # RSI oversold - potential buy signal
        if rsi <= self.parameters["oversold_threshold"]:
            signal_type = SignalType.BUY
            # Stronger signal the more oversold
            strength = min(1.0, (self.parameters["oversold_threshold"] - rsi) / 20)
            confidence = min(0.9, strength + 0.3)
        
        # RSI overbought - potential sell signal
        elif rsi >= self.parameters["overbought_threshold"]:
            signal_type = SignalType.SELL
            # Stronger signal the more overbought
            strength = min(1.0, (rsi - self.parameters["overbought_threshold"]) / 20)
            confidence = min(0.9, strength + 0.3)
        
        # Only generate signal if strength meets minimum threshold
        if abs(strength) < self.parameters["min_strength"]:
            return None
        
        return StrategySignal(
            symbol=tick.symbol,
            signal=signal_type,
            strength=strength if signal_type == SignalType.BUY else -strength,
            confidence=confidence,
            price=tick.price,
            timestamp=tick.ts,
            metadata={
                "rsi": rsi,
                "oversold_threshold": self.parameters["oversold_threshold"],
                "overbought_threshold": self.parameters["overbought_threshold"],
            }
        )


class MACDStrategy(BaseStrategy):
    """MACD crossover strategy."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "min_histogram": 0.001,  # Minimum MACD histogram for signal
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("MACD_Strategy", symbols, default_params)
        
        # Track previous MACD values for crossover detection
        self.prev_macd: Dict[str, Optional[float]] = {symbol: None for symbol in symbols}
        self.prev_signal: Dict[str, Optional[float]] = {symbol: None for symbol in symbols}
    
    def get_required_history_length(self) -> int:
        return self.parameters["slow_period"] + self.parameters["signal_period"] + 10
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate MACD crossover signals."""
        if not self.is_active:
            return None
        
        indicators = self.get_current_indicators(tick.symbol)
        macd_line = indicators.get("macd_line")
        signal_line = indicators.get("macd_signal")
        histogram = indicators.get("macd_histogram")
        
        if macd_line is None or signal_line is None or histogram is None:
            return None
        
        # Check for crossovers
        prev_macd = self.prev_macd[tick.symbol]
        prev_signal = self.prev_signal[tick.symbol]
        
        signal_type = SignalType.HOLD
        strength = 0.0
        confidence = 0.0
        
        if prev_macd is not None and prev_signal is not None:
            # Bullish crossover: MACD crosses above signal line
            if prev_macd <= prev_signal and macd_line > signal_line:
                if abs(histogram) >= self.parameters["min_histogram"]:
                    signal_type = SignalType.BUY
                    strength = min(1.0, abs(histogram) * 100)  # Scale histogram
                    confidence = 0.7
            
            # Bearish crossover: MACD crosses below signal line
            elif prev_macd >= prev_signal and macd_line < signal_line:
                if abs(histogram) >= self.parameters["min_histogram"]:
                    signal_type = SignalType.SELL
                    strength = min(1.0, abs(histogram) * 100)
                    confidence = 0.7
        
        # Update previous values
        self.prev_macd[tick.symbol] = macd_line
        self.prev_signal[tick.symbol] = signal_line
        
        if signal_type == SignalType.HOLD:
            return None
        
        return StrategySignal(
            symbol=tick.symbol,
            signal=signal_type,
            strength=strength if signal_type == SignalType.BUY else -strength,
            confidence=confidence,
            price=tick.price,
            timestamp=tick.ts,
            metadata={
                "macd_line": macd_line,
                "signal_line": signal_line,
                "histogram": histogram,
                "crossover_type": "bullish" if signal_type == SignalType.BUY else "bearish",
            }
        )


class MomentumStrategy(BaseStrategy):
    """Price momentum strategy with multiple timeframes."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "short_period": 10,
            "long_period": 30,
            "momentum_threshold": 0.02,  # 2% price change threshold
            "volume_confirmation": True,
            "volume_multiplier": 1.5,  # Volume should be 1.5x average
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("Momentum_Strategy", symbols, default_params)
    
    def get_required_history_length(self) -> int:
        return max(self.parameters["long_period"], 50) + 10
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate momentum-based signals."""
        if not self.is_active:
            return None
        
        price_history = self.get_price_history(tick.symbol, 100)
        if len(price_history) < self.parameters["long_period"]:
            return None
        
        indicators = self.get_current_indicators(tick.symbol)
        
        # Calculate short and long term momentum
        short_prices = [t.price for t in price_history[-self.parameters["short_period"]:]]
        long_prices = [t.price for t in price_history[-self.parameters["long_period"]:]]
        
        short_momentum = (short_prices[-1] - short_prices[0]) / short_prices[0]
        long_momentum = (long_prices[-1] - long_prices[0]) / long_prices[0]
        
        # Volume confirmation
        volume_confirmed = True
        if self.parameters["volume_confirmation"]:
            current_volume = tick.volume
            avg_volume = indicators.get("volume_sma", 0)
            volume_confirmed = current_volume >= avg_volume * self.parameters["volume_multiplier"]
        
        signal_type = SignalType.HOLD
        strength = 0.0
        confidence = 0.0
        
        # Strong upward momentum
        if (short_momentum > self.parameters["momentum_threshold"] and 
            long_momentum > 0 and volume_confirmed):
            signal_type = SignalType.BUY
            strength = min(1.0, short_momentum * 10)  # Scale momentum
            confidence = 0.6 + (0.3 if volume_confirmed else 0)
        
        # Strong downward momentum
        elif (short_momentum < -self.parameters["momentum_threshold"] and 
              long_momentum < 0 and volume_confirmed):
            signal_type = SignalType.SELL
            strength = min(1.0, abs(short_momentum) * 10)
            confidence = 0.6 + (0.3 if volume_confirmed else 0)
        
        if signal_type == SignalType.HOLD:
            return None
        
        return StrategySignal(
            symbol=tick.symbol,
            signal=signal_type,
            strength=strength if signal_type == SignalType.BUY else -strength,
            confidence=confidence,
            price=tick.price,
            timestamp=tick.ts,
            metadata={
                "short_momentum": short_momentum,
                "long_momentum": long_momentum,
                "volume_confirmed": volume_confirmed,
                "current_volume": tick.volume,
                "avg_volume": indicators.get("volume_sma", 0),
            }
        )


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands mean reversion strategy."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.01,  # Band width threshold for squeeze
            "breakout_confirmation": True,
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("BollingerBands_Strategy", symbols, default_params)
    
    def get_required_history_length(self) -> int:
        return self.parameters["bb_period"] + 10
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate Bollinger Bands signals."""
        if not self.is_active:
            return None
        
        indicators = self.get_current_indicators(tick.symbol)
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        sma_20 = indicators.get("sma_20")
        
        if bb_upper is None or bb_lower is None or sma_20 is None:
            return None
        
        current_price = tick.price
        band_width = (bb_upper - bb_lower) / sma_20
        
        signal_type = SignalType.HOLD
        strength = 0.0
        confidence = 0.0
        
        # Price touching lower band - potential buy
        if current_price <= bb_lower * 1.01:  # Small tolerance
            signal_type = SignalType.BUY
            strength = min(1.0, (bb_lower - current_price) / bb_lower * 10)
            confidence = 0.7
        
        # Price touching upper band - potential sell
        elif current_price >= bb_upper * 0.99:  # Small tolerance
            signal_type = SignalType.SELL
            strength = min(1.0, (current_price - bb_upper) / bb_upper * 10)
            confidence = 0.7
        
        # Bollinger squeeze breakout
        elif band_width < self.parameters["squeeze_threshold"]:
            # Wait for breakout direction
            if current_price > sma_20 * 1.005:  # Upward breakout
                signal_type = SignalType.BUY
                strength = 0.8
                confidence = 0.8
            elif current_price < sma_20 * 0.995:  # Downward breakout
                signal_type = SignalType.SELL
                strength = 0.8
                confidence = 0.8
        
        if signal_type == SignalType.HOLD:
            return None
        
        return StrategySignal(
            symbol=tick.symbol,
            signal=signal_type,
            strength=strength if signal_type == SignalType.BUY else -strength,
            confidence=confidence,
            price=tick.price,
            timestamp=tick.ts,
            metadata={
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "sma_20": sma_20,
                "band_width": band_width,
                "squeeze_detected": band_width < self.parameters["squeeze_threshold"],
            }
        )


class MultiTimeframeStrategy(BaseStrategy):
    """Multi-timeframe trend following strategy."""
    
    def __init__(self, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "fast_ma": 10,
            "medium_ma": 20,
            "slow_ma": 50,
            "trend_alignment_required": True,
            "min_trend_strength": 0.5,
        }
        if parameters:
            default_params.update(parameters)
        
        super().__init__("MultiTimeframe_Strategy", symbols, default_params)
    
    def get_required_history_length(self) -> int:
        return self.parameters["slow_ma"] + 10
    
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate multi-timeframe signals."""
        if not self.is_active:
            return None
        
        price_history = self.get_price_history(tick.symbol, 100)
        if len(price_history) < self.parameters["slow_ma"]:
            return None
        
        prices = [t.price for t in price_history]
        
        # Calculate moving averages
        fast_ma = self._calculate_sma(prices, self.parameters["fast_ma"])
        medium_ma = self._calculate_sma(prices, self.parameters["medium_ma"])
        slow_ma = self._calculate_sma(prices, self.parameters["slow_ma"])
        
        if fast_ma is None or medium_ma is None or slow_ma is None:
            return None
        
        current_price = tick.price
        
        # Determine trend alignment
        uptrend_aligned = fast_ma > medium_ma > slow_ma and current_price > fast_ma
        downtrend_aligned = fast_ma < medium_ma < slow_ma and current_price < fast_ma
        
        signal_type = SignalType.HOLD
        strength = 0.0
        confidence = 0.0
        
        if uptrend_aligned:
            signal_type = SignalType.BUY
            # Strength based on how well aligned the MAs are
            ma_spread = (fast_ma - slow_ma) / slow_ma
            strength = min(1.0, ma_spread * 20)
            confidence = 0.8
        
        elif downtrend_aligned:
            signal_type = SignalType.SELL
            ma_spread = (slow_ma - fast_ma) / slow_ma
            strength = min(1.0, ma_spread * 20)
            confidence = 0.8
        
        # Check minimum trend strength
        if abs(strength) < self.parameters["min_trend_strength"]:
            return None
        
        if signal_type == SignalType.HOLD:
            return None
        
        return StrategySignal(
            symbol=tick.symbol,
            signal=signal_type,
            strength=strength if signal_type == SignalType.BUY else -strength,
            confidence=confidence,
            price=tick.price,
            timestamp=tick.ts,
            metadata={
                "fast_ma": fast_ma,
                "medium_ma": medium_ma,
                "slow_ma": slow_ma,
                "trend_aligned": uptrend_aligned or downtrend_aligned,
                "trend_direction": "up" if uptrend_aligned else "down" if downtrend_aligned else "sideways",
            }
        )