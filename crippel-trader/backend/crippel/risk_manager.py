"""Advanced risk management system with dynamic aggression-based controls."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import structlog
import numpy as np
from pydantic import BaseModel

from .config import get_settings
from .models.core import Order, Position, PriceTick, OrderSide, PortfolioState
from .notifications import get_notification_service


class RiskLevel(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAlert(BaseModel):
    """Risk management alert."""
    level: RiskLevel
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    action_required: bool = False


@dataclass
class RiskMetrics:
    """Current risk metrics."""
    portfolio_var: float  # Value at Risk
    max_drawdown: float
    current_drawdown: float
    position_concentration: float
    leverage_ratio: float
    correlation_risk: float
    volatility_risk: float
    liquidity_risk: float


class RiskManager:
    """Advanced risk management system with dynamic controls."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        self.notification_service = get_notification_service()
        
        # Risk state
        self.current_aggression = self.settings.default_aggression
        self.risk_limits = self._calculate_dynamic_limits(self.current_aggression)
        self.active_alerts: List[RiskAlert] = []
        self.risk_history: List[Tuple[datetime, RiskMetrics]] = []
        
        # Portfolio tracking
        self.max_equity = 0.0
        self.equity_history: List[Tuple[datetime, float]] = []
        self.position_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Volatility tracking
        self.price_volatility: Dict[str, float] = {}
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}
        
        self.logger.info("Risk manager initialized", aggression=self.current_aggression)
    
    def _calculate_dynamic_limits(self, aggression: int) -> Dict[str, float]:
        """Calculate risk limits based on aggression level (1-10)."""
        # Base limits for aggression level 1 (most conservative)
        base_limits = {
            "max_drawdown": 0.05,      # 5%
            "per_trade_risk": 0.01,    # 1%
            "per_symbol_exposure": 0.10, # 10%
            "total_leverage": 1.0,     # No leverage
            "var_limit": 0.02,         # 2% daily VaR
            "concentration_limit": 0.25, # 25% max in single position
            "correlation_limit": 0.7,   # Max correlation between positions
            "volatility_limit": 0.30,   # 30% annualized volatility
        }
        
        # Scale factors based on aggression (1-10)
        scale_factors = {
            "max_drawdown": 1.0 + (aggression - 1) * 0.5,      # 5% to 50%
            "per_trade_risk": 1.0 + (aggression - 1) * 1.9,    # 1% to 20%
            "per_symbol_exposure": 1.0 + (aggression - 1) * 0.9, # 10% to 100%
            "total_leverage": 1.0 + (aggression - 1) * 0.33,   # 1x to 4x
            "var_limit": 1.0 + (aggression - 1) * 2.0,         # 2% to 20%
            "concentration_limit": 1.0 + (aggression - 1) * 2.0, # 25% to 75%
            "correlation_limit": 1.0 + (aggression - 1) * 0.033, # 0.7 to 1.0
            "volatility_limit": 1.0 + (aggression - 1) * 1.0,   # 30% to 60%
        }
        
        return {
            key: base_limits[key] * scale_factors[key]
            for key in base_limits
        }
    
    async def set_aggression(self, aggression: int) -> None:
        """Update aggression level and recalculate risk limits."""
        if not 1 <= aggression <= 10:
            raise ValueError("Aggression must be between 1 and 10")
        
        old_aggression = self.current_aggression
        self.current_aggression = aggression
        self.risk_limits = self._calculate_dynamic_limits(aggression)
        
        self.logger.info(
            "Risk aggression updated",
            old_aggression=old_aggression,
            new_aggression=aggression,
            new_limits=self.risk_limits
        )
        
        await self.notification_service.send_system_alert(
            "Risk Profile Updated",
            f"Aggression changed from {old_aggression} to {aggression}. "
            f"Max drawdown: {self.risk_limits['max_drawdown']:.1%}, "
            f"Per-trade risk: {self.risk_limits['per_trade_risk']:.1%}",
            "info"
        )
    
    async def validate_order(
        self, 
        order: Order, 
        portfolio: PortfolioState,
        current_prices: Dict[str, PriceTick]
    ) -> Tuple[bool, Optional[str]]:
        """Validate order against risk limits."""
        try:
            # Check if we have price data
            if order.symbol not in current_prices:
                return False, f"No price data available for {order.symbol}"
            
            current_price = current_prices[order.symbol].price
            order_value = order.size * current_price
            
            # 1. Per-trade risk limit
            max_trade_value = portfolio.equity * self.risk_limits["per_trade_risk"]
            if order_value > max_trade_value:
                return False, (
                    f"Order value ${order_value:.2f} exceeds per-trade limit "
                    f"${max_trade_value:.2f} ({self.risk_limits['per_trade_risk']:.1%})"
                )
            
            # 2. Per-symbol exposure limit
            current_position = portfolio.positions.get(order.symbol, Position(symbol=order.symbol))
            
            if order.side == OrderSide.BUY:
                new_position_size = current_position.size + order.size
            else:
                new_position_size = max(0, current_position.size - order.size)
            
            new_position_value = new_position_size * current_price
            max_symbol_value = portfolio.equity * self.risk_limits["per_symbol_exposure"]
            
            if new_position_value > max_symbol_value:
                return False, (
                    f"Position would be ${new_position_value:.2f}, exceeding symbol limit "
                    f"${max_symbol_value:.2f} ({self.risk_limits['per_symbol_exposure']:.1%})"
                )
            
            # 3. Portfolio concentration check
            total_position_value = sum(
                pos.size * current_prices.get(symbol, PriceTick(symbol=symbol, price=0, volume=0, ts=datetime.utcnow())).price
                for symbol, pos in portfolio.positions.items()
                if pos.size > 0 and symbol in current_prices
            )
            
            if order.side == OrderSide.BUY:
                total_position_value += order_value
            
            concentration = new_position_value / max(total_position_value, 1.0)
            if concentration > self.risk_limits["concentration_limit"]:
                return False, (
                    f"Position concentration {concentration:.1%} exceeds limit "
                    f"{self.risk_limits['concentration_limit']:.1%}"
                )
            
            # 4. Volatility check
            symbol_volatility = self.price_volatility.get(order.symbol, 0.0)
            if symbol_volatility > self.risk_limits["volatility_limit"]:
                return False, (
                    f"Symbol volatility {symbol_volatility:.1%} exceeds limit "
                    f"{self.risk_limits['volatility_limit']:.1%}"
                )
            
            # 5. Cash availability for buy orders
            if order.side == OrderSide.BUY:
                required_cash = order_value * 1.01  # Include estimated fees
                if required_cash > portfolio.cash:
                    return False, f"Insufficient cash: need ${required_cash:.2f}, have ${portfolio.cash:.2f}"
            
            return True, None
            
        except Exception as e:
            self.logger.error("Error validating order", order=order, error=str(e))
            return False, f"Validation error: {str(e)}"
    
    async def assess_portfolio_risk(
        self, 
        portfolio: PortfolioState,
        current_prices: Dict[str, PriceTick]
    ) -> RiskMetrics:
        """Assess current portfolio risk metrics."""
        try:
            # Update equity history
            current_equity = portfolio.equity
            now = datetime.utcnow()
            self.equity_history.append((now, current_equity))
            
            # Keep only last 30 days
            cutoff = now - timedelta(days=30)
            self.equity_history = [(ts, eq) for ts, eq in self.equity_history if ts > cutoff]
            
            # Update max equity and calculate drawdown
            if current_equity > self.max_equity:
                self.max_equity = current_equity
            
            current_drawdown = (self.max_equity - current_equity) / self.max_equity if self.max_equity > 0 else 0.0
            
            # Calculate max drawdown over history
            max_drawdown = 0.0
            peak_equity = 0.0
            for _, equity in self.equity_history:
                if equity > peak_equity:
                    peak_equity = equity
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calculate portfolio VaR (95% confidence, 1-day)
            if len(self.equity_history) >= 30:
                returns = []
                for i in range(1, len(self.equity_history)):
                    prev_equity = self.equity_history[i-1][1]
                    curr_equity = self.equity_history[i][1]
                    if prev_equity > 0:
                        returns.append((curr_equity - prev_equity) / prev_equity)
                
                if returns:
                    portfolio_var = abs(np.percentile(returns, 5)) * current_equity
                else:
                    portfolio_var = 0.0
            else:
                portfolio_var = 0.0
            
            # Calculate position concentration
            total_position_value = 0.0
            max_position_value = 0.0
            
            for symbol, position in portfolio.positions.items():
                if position.size > 0 and symbol in current_prices:
                    position_value = position.size * current_prices[symbol].price
                    total_position_value += position_value
                    max_position_value = max(max_position_value, position_value)
            
            position_concentration = max_position_value / max(total_position_value, 1.0)
            
            # Calculate leverage ratio
            leverage_ratio = total_position_value / max(current_equity, 1.0)
            
            # Calculate correlation risk (simplified)
            correlation_risk = self._calculate_correlation_risk(portfolio, current_prices)
            
            # Calculate volatility risk
            volatility_risk = self._calculate_volatility_risk(portfolio, current_prices)
            
            # Calculate liquidity risk (simplified)
            liquidity_risk = self._calculate_liquidity_risk(portfolio, current_prices)
            
            metrics = RiskMetrics(
                portfolio_var=portfolio_var,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                position_concentration=position_concentration,
                leverage_ratio=leverage_ratio,
                correlation_risk=correlation_risk,
                volatility_risk=volatility_risk,
                liquidity_risk=liquidity_risk
            )
            
            # Store risk history
            self.risk_history.append((now, metrics))
            if len(self.risk_history) > 1000:  # Keep last 1000 entries
                self.risk_history = self.risk_history[-1000:]
            
            # Check for risk alerts
            await self._check_risk_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error("Error assessing portfolio risk", error=str(e))
            return RiskMetrics(
                portfolio_var=0.0,
                max_drawdown=0.0,
                current_drawdown=0.0,
                position_concentration=0.0,
                leverage_ratio=0.0,
                correlation_risk=0.0,
                volatility_risk=0.0,
                liquidity_risk=0.0
            )
    
    def _calculate_correlation_risk(
        self, 
        portfolio: PortfolioState,
        current_prices: Dict[str, PriceTick]
    ) -> float:
        """Calculate portfolio correlation risk."""
        # Simplified correlation risk calculation
        # In a full implementation, you would calculate actual correlations
        active_positions = [
            symbol for symbol, pos in portfolio.positions.items()
            if pos.size > 0 and symbol in current_prices
        ]
        
        if len(active_positions) <= 1:
            return 0.0
        
        # Assume higher correlation risk with more positions in same asset class
        crypto_positions = sum(1 for symbol in active_positions if any(crypto in symbol for crypto in ["BTC", "ETH", "ADA", "SOL"]))
        stock_positions = len(active_positions) - crypto_positions
        
        # Higher risk if concentrated in one asset class
        if crypto_positions > 0 and stock_positions == 0:
            return min(0.8, crypto_positions * 0.2)
        elif stock_positions > 0 and crypto_positions == 0:
            return min(0.8, stock_positions * 0.15)
        else:
            return 0.3  # Diversified across asset classes
    
    def _calculate_volatility_risk(
        self, 
        portfolio: PortfolioState,
        current_prices: Dict[str, PriceTick]
    ) -> float:
        """Calculate portfolio volatility risk."""
        total_value = 0.0
        weighted_volatility = 0.0
        
        for symbol, position in portfolio.positions.items():
            if position.size > 0 and symbol in current_prices:
                position_value = position.size * current_prices[symbol].price
                symbol_volatility = self.price_volatility.get(symbol, 0.3)  # Default 30%
                
                total_value += position_value
                weighted_volatility += position_value * symbol_volatility
        
        return weighted_volatility / max(total_value, 1.0)
    
    def _calculate_liquidity_risk(
        self, 
        portfolio: PortfolioState,
        current_prices: Dict[str, PriceTick]
    ) -> float:
        """Calculate portfolio liquidity risk."""
        # Simplified liquidity risk based on position sizes and spreads
        total_risk = 0.0
        total_value = 0.0
        
        for symbol, position in portfolio.positions.items():
            if position.size > 0 and symbol in current_prices:
                tick = current_prices[symbol]
                position_value = position.size * tick.price
                
                # Calculate spread as proxy for liquidity
                spread_pct = tick.spread / tick.price if tick.price > 0 and tick.spread > 0 else 0.01
                
                # Higher risk for larger positions with wider spreads
                position_risk = spread_pct * (position_value / max(portfolio.equity, 1.0))
                
                total_risk += position_risk * position_value
                total_value += position_value
        
        return total_risk / max(total_value, 1.0)
    
    async def _check_risk_alerts(self, metrics: RiskMetrics) -> None:
        """Check risk metrics against limits and generate alerts."""
        alerts = []
        
        # Drawdown alerts
        if metrics.current_drawdown > self.risk_limits["max_drawdown"]:
            alerts.append(RiskAlert(
                level=RiskLevel.CRITICAL,
                message=f"Current drawdown {metrics.current_drawdown:.1%} exceeds limit {self.risk_limits['max_drawdown']:.1%}",
                metric_name="current_drawdown",
                current_value=metrics.current_drawdown,
                threshold=self.risk_limits["max_drawdown"],
                timestamp=datetime.utcnow(),
                action_required=True
            ))
        elif metrics.current_drawdown > self.risk_limits["max_drawdown"] * 0.8:
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                message=f"Current drawdown {metrics.current_drawdown:.1%} approaching limit {self.risk_limits['max_drawdown']:.1%}",
                metric_name="current_drawdown",
                current_value=metrics.current_drawdown,
                threshold=self.risk_limits["max_drawdown"],
                timestamp=datetime.utcnow()
            ))
        
        # VaR alerts
        if metrics.portfolio_var > self.risk_limits["var_limit"]:
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                message=f"Portfolio VaR {metrics.portfolio_var:.1%} exceeds limit {self.risk_limits['var_limit']:.1%}",
                metric_name="portfolio_var",
                current_value=metrics.portfolio_var,
                threshold=self.risk_limits["var_limit"],
                timestamp=datetime.utcnow()
            ))
        
        # Concentration alerts
        if metrics.position_concentration > self.risk_limits["concentration_limit"]:
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                message=f"Position concentration {metrics.position_concentration:.1%} exceeds limit {self.risk_limits['concentration_limit']:.1%}",
                metric_name="position_concentration",
                current_value=metrics.position_concentration,
                threshold=self.risk_limits["concentration_limit"],
                timestamp=datetime.utcnow()
            ))
        
        # Leverage alerts
        if metrics.leverage_ratio > self.risk_limits["total_leverage"]:
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                message=f"Leverage ratio {metrics.leverage_ratio:.1f}x exceeds limit {self.risk_limits['total_leverage']:.1f}x",
                metric_name="leverage_ratio",
                current_value=metrics.leverage_ratio,
                threshold=self.risk_limits["total_leverage"],
                timestamp=datetime.utcnow()
            ))
        
        # Send new alerts
        for alert in alerts:
            if not any(
                existing.metric_name == alert.metric_name and 
                existing.level == alert.level and
                (datetime.utcnow() - existing.timestamp).seconds < 3600  # Don't spam same alert within 1 hour
                for existing in self.active_alerts
            ):
                await self._send_risk_alert(alert)
                self.active_alerts.append(alert)
        
        # Clean up old alerts
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.active_alerts = [alert for alert in self.active_alerts if alert.timestamp > cutoff]
    
    async def _send_risk_alert(self, alert: RiskAlert) -> None:
        """Send risk alert notification."""
        severity_map = {
            RiskLevel.LOW: "info",
            RiskLevel.MEDIUM: "warning", 
            RiskLevel.HIGH: "warning",
            RiskLevel.CRITICAL: "error"
        }
        
        await self.notification_service.send_risk_alert(
            alert_type=alert.metric_name.replace("_", " ").title(),
            current_value=alert.current_value * 100,  # Convert to percentage
            threshold=alert.threshold * 100,
            action_taken="Monitoring" if not alert.action_required else "Action Required"
        )
    
    async def update_price_volatility(self, symbol: str, prices: List[float]) -> None:
        """Update volatility estimate for a symbol."""
        if len(prices) < 2:
            return
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if returns:
            # Annualized volatility (assuming daily returns)
            volatility = np.std(returns) * np.sqrt(252)
            self.price_volatility[symbol] = volatility
    
    def get_risk_summary(self) -> Dict:
        """Get risk summary for dashboard."""
        if not self.risk_history:
            return {
                "current_aggression": self.current_aggression,
                "risk_limits": self.risk_limits,
                "active_alerts": len(self.active_alerts),
                "metrics": None
            }
        
        latest_metrics = self.risk_history[-1][1]
        
        return {
            "current_aggression": self.current_aggression,
            "risk_limits": self.risk_limits,
            "active_alerts": len(self.active_alerts),
            "critical_alerts": len([a for a in self.active_alerts if a.level == RiskLevel.CRITICAL]),
            "metrics": {
                "portfolio_var": latest_metrics.portfolio_var,
                "max_drawdown": latest_metrics.max_drawdown,
                "current_drawdown": latest_metrics.current_drawdown,
                "position_concentration": latest_metrics.position_concentration,
                "leverage_ratio": latest_metrics.leverage_ratio,
                "correlation_risk": latest_metrics.correlation_risk,
                "volatility_risk": latest_metrics.volatility_risk,
                "liquidity_risk": latest_metrics.liquidity_risk,
            }
        }