"""Statistics service for KPIs."""
from __future__ import annotations

from ..models.core import PortfolioState, TradeStat


def summarize(portfolio: PortfolioState, stats: TradeStat) -> dict[str, float]:
    """Return KPI values."""
    total_equity = portfolio.total_equity
    return {
        "pnl": stats.realized_pnl + portfolio.pnl_unrealized,
        "fees": stats.fees_paid,
        "win_rate": stats.win_rate,
        "total_trades": float(stats.total_trades),
        "equity": total_equity,
        "cash": portfolio.cash,
    }
