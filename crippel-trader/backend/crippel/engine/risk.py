"""Risk management logic."""
from __future__ import annotations

from dataclasses import dataclass

from ..models.core import PortfolioState, RiskLimits
from ..models.enums import OrderSide


@dataclass
class RiskManager:
    """Evaluate whether new trades comply with configured limits."""

    limits: RiskLimits

    def can_trade(
        self,
        portfolio: PortfolioState,
        symbol: str,
        side: OrderSide,
        size: float,
        price: float,
    ) -> bool:
        equity = portfolio.total_equity
        if equity <= 0:
            return False
        position = portfolio.positions.get(symbol)
        current_notional = abs(position.size) * price if position else 0.0
        projected_notional = current_notional
        trade_notional = size * price
        if side == OrderSide.BUY:
            projected_notional += trade_notional
        else:
            projected_notional = max(0.0, projected_notional - trade_notional)
        if trade_notional > equity * self.limits.per_trade_cap:
            return False
        if projected_notional > equity * self.limits.per_symbol_exposure:
            return False
        drawdown = -portfolio.pnl_realized
        if drawdown > equity * self.limits.drawdown_limit:
            return False
        return True
