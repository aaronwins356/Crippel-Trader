"""Base strategy interface and common functionality."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import structlog
import numpy as np
from pydantic import BaseModel

from ..models.core import PriceTick, Order, OrderSide, OrderType, Mode
from ..config import get_settings


class SignalType(Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class StrategySignal(BaseModel):
    """Strategy signal output."""
    symbol: str
    signal: SignalType
    strength: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    price: float
    timestamp: datetime
    metadata: Dict[str, Any] = {}


@dataclass
class StrategyPerformance:
    """Strategy performance metrics."""
    total_signals: int = 0
    profitable_signals: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    last_updated: datetime = datetime.utcnow()


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, name: str, symbols: List[str], parameters: Optional[Dict[str, Any]] = None):
        self.name = name
        self.symbols = symbols
        self.parameters = parameters or {}
        self.settings = get_settings()
        self.logger = structlog.get_logger(f"strategy.{name}")
        
        # Strategy state
        self.is_active = True
        self.price_history: Dict[str, List[PriceTick]] = {symbol: [] for symbol in symbols}
        self.signals_history: List[StrategySignal] = []
        self.performance = StrategyPerformance()
        
        # Technical indicators cache
        self.indicators: Dict[str, Dict[str, Any]] = {symbol: {} for symbol in symbols}
        
        self.logger.info("Strategy initialized", name=name, symbols=symbols, parameters=parameters)
    
    @abstractmethod
    async def generate_signal(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Generate trading signal based on market data."""
        pass
    
    @abstractmethod
    def get_required_history_length(self) -> int:
        """Return minimum number of price ticks required for signal generation."""
        pass
    
    async def update_market_data(self, tick: PriceTick) -> Optional[StrategySignal]:
        """Update market data and potentially generate signal."""
        if tick.symbol not in self.symbols:
            return None
        
        # Store price data
        self.price_history[tick.symbol].append(tick)
        
        # Keep only required history to manage memory
        max_history = max(1000, self.get_required_history_length() * 2)
        if len(self.price_history[tick.symbol]) > max_history:
            self.price_history[tick.symbol] = self.price_history[tick.symbol][-max_history:]
        
        # Update technical indicators
        await self._update_indicators(tick)
        
        # Generate signal if we have enough data
        if len(self.price_history[tick.symbol]) >= self.get_required_history_length():
            signal = await self.generate_signal(tick)
            if signal:
                self.signals_history.append(signal)
                # Keep last 1000 signals
                if len(self.signals_history) > 1000:
                    self.signals_history = self.signals_history[-1000:]
                
                self.logger.info("Signal generated", signal=signal)
                return signal
        
        return None
    
    async def _update_indicators(self, tick: PriceTick) -> None:
        """Update technical indicators for the symbol."""
        symbol = tick.symbol
        prices = [t.price for t in self.price_history[symbol]]
        volumes = [t.volume for t in self.price_history[symbol]]
        
        if len(prices) < 2:
            return
        
        # Update common indicators
        self.indicators[symbol].update({
            "sma_20": self._calculate_sma(prices, 20),
            "sma_50": self._calculate_sma(prices, 50),
            "ema_12": self._calculate_ema(prices, 12),
            "ema_26": self._calculate_ema(prices, 26),
            "rsi_14": self._calculate_rsi(prices, 14),
            "bb_upper": self._calculate_bollinger_bands(prices, 20)[0],
            "bb_lower": self._calculate_bollinger_bands(prices, 20)[1],
            "volume_sma": self._calculate_sma(volumes, 20),
            "price_change": (prices[-1] - prices[-2]) / prices[-2] if len(prices) >= 2 else 0.0,
            "volatility": self._calculate_volatility(prices, 20),
        })
        
        # Calculate MACD
        if len(prices) >= 26:
            macd_line, signal_line = self._calculate_macd(prices)
            self.indicators[symbol].update({
                "macd_line": macd_line,
                "macd_signal": signal_line,
                "macd_histogram": macd_line - signal_line if macd_line and signal_line else 0.0,
            })
    
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> tuple[Optional[float], Optional[float]]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return None, None
        
        sma = self._calculate_sma(prices, period)
        if sma is None:
            return None, None
        
        variance = sum((price - sma) ** 2 for price in prices[-period:]) / period
        std = variance ** 0.5
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, lower_band
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[Optional[float], Optional[float]]:
        """Calculate MACD."""
        if len(prices) < slow:
            return None, None
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        if ema_fast is None or ema_slow is None:
            return None, None
        
        macd_line = ema_fast - ema_slow
        
        # For signal line, we'd need to calculate EMA of MACD line
        # Simplified version - in practice you'd maintain MACD history
        signal_line = macd_line  # Placeholder
        
        return macd_line, signal_line
    
    def _calculate_volatility(self, prices: List[float], period: int = 20) -> Optional[float]:
        """Calculate price volatility."""
        if len(prices) < period:
            return None
        
        returns = []
        for i in range(1, len(prices[-period:])):
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return None
        
        return np.std(returns)
    
    def get_current_indicators(self, symbol: str) -> Dict[str, Any]:
        """Get current technical indicators for symbol."""
        return self.indicators.get(symbol, {})
    
    def get_price_history(self, symbol: str, periods: int = 100) -> List[PriceTick]:
        """Get recent price history for symbol."""
        history = self.price_history.get(symbol, [])
        return history[-periods:] if len(history) > periods else history
    
    def update_performance(self, pnl: float, is_profitable: bool) -> None:
        """Update strategy performance metrics."""
        self.performance.total_signals += 1
        self.performance.total_pnl += pnl
        
        if is_profitable:
            self.performance.profitable_signals += 1
        
        self.performance.win_rate = self.performance.profitable_signals / self.performance.total_signals
        self.performance.avg_return = self.performance.total_pnl / self.performance.total_signals
        self.performance.last_updated = datetime.utcnow()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get strategy performance summary."""
        return {
            "name": self.name,
            "is_active": self.is_active,
            "total_signals": self.performance.total_signals,
            "win_rate": self.performance.win_rate,
            "total_pnl": self.performance.total_pnl,
            "avg_return": self.performance.avg_return,
            "max_drawdown": self.performance.max_drawdown,
            "sharpe_ratio": self.performance.sharpe_ratio,
            "last_signal": self.signals_history[-1].timestamp if self.signals_history else None,
        }
    
    def activate(self) -> None:
        """Activate the strategy."""
        self.is_active = True
        self.logger.info("Strategy activated", name=self.name)
    
    def deactivate(self) -> None:
        """Deactivate the strategy."""
        self.is_active = False
        self.logger.info("Strategy deactivated", name=self.name)
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy parameters."""
        self.parameters.update(parameters)
        self.logger.info("Strategy parameters updated", name=self.name, parameters=parameters)