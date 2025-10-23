"""Portfolio management service mirroring the legacy JavaScript behaviour."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from ..utils.logger import get_child

logger = get_child("portfolio")


@dataclass
class Trade:
    id: str
    timestamp: str
    symbol: str
    quantity: float
    price: float
    notional: float
    reason: str
    strategy: str
    sector: Optional[str]


class PortfolioService:
    """Track simulated positions, cash balances and trade history."""

    def __init__(self, initial_capital: float = 250_000.0) -> None:
        self.initial_capital = float(initial_capital)
        self.cash = float(initial_capital)
        self.positions: Dict[str, Dict[str, float]] = {}
        self.trades: List[Trade] = []
        self.realized_pnl = 0.0

    def get_equity(self, market_snapshots: Optional[Dict[str, Dict[str, float]]] = None) -> float:
        market_snapshots = market_snapshots or {}
        position_value = 0.0
        for position in self.positions.values():
            latest_price = market_snapshots.get(position["symbol"], {}).get(
                "price", position["avg_price"]
            )
            position_value += position["quantity"] * latest_price
        return self.cash + position_value + self.realized_pnl

    def get_state(self, market_snapshots: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, object]:
        market_snapshots = market_snapshots or {}
        positions = []
        for position in self.positions.values():
            latest_price = market_snapshots.get(position["symbol"], {}).get(
                "price", position["avg_price"]
            )
            market_value = position["quantity"] * latest_price
            unrealized = (latest_price - position["avg_price"]) * position["quantity"]
            positions.append(
                {
                    "symbol": position["symbol"],
                    "quantity": position["quantity"],
                    "avgPrice": position["avg_price"],
                    "sector": position.get("sector"),
                    "latestPrice": latest_price,
                    "marketValue": market_value,
                    "unrealizedPnL": unrealized,
                }
            )

        gross_exposure = sum(abs(pos["marketValue"]) for pos in positions)
        net_exposure = sum(pos["marketValue"] for pos in positions)
        equity = self.get_equity(market_snapshots)

        return {
            "cash": self.cash,
            "positions": positions,
            "trades": [trade.__dict__ for trade in self.trades[-200:]],
            "realizedPnL": self.realized_pnl,
            "grossExposure": gross_exposure,
            "netExposure": net_exposure,
            "leverage": 0 if not gross_exposure or not equity else gross_exposure / equity,
            "equity": equity,
        }

    def apply_trade(
        self,
        *,
        symbol: str,
        quantity: float,
        price: float,
        reason: str = "manual",
        strategy: str = "discretionary",
        sector: Optional[str] = None,
    ) -> Dict[str, object]:
        if not symbol or quantity == 0 or not isinstance(quantity, (int, float)):
            raise ValueError("Invalid trade payload")
        if not isinstance(price, (int, float)):
            raise ValueError("Invalid trade payload")

        quantity = float(quantity)
        price = float(price)

        existing = self.positions.get(symbol, {
            "symbol": symbol,
            "quantity": 0.0,
            "avg_price": price,
            "sector": sector,
        })

        trade_direction = 1 if quantity > 0 else -1
        position_direction = 1 if existing["quantity"] > 0 else (-1 if existing["quantity"] < 0 else 0)
        notional = quantity * price

        if trade_direction > 0 and self.cash < notional:
            raise ValueError("Insufficient cash to execute trade")

        new_quantity = existing["quantity"] + quantity
        closing_quantity = 0.0
        if position_direction != 0 and trade_direction != position_direction:
            closing_quantity = min(abs(quantity), abs(existing["quantity"]))

        if closing_quantity > 0:
            pnl = (price - existing["avg_price"]) * closing_quantity * position_direction
            self.realized_pnl += pnl

        if new_quantity == 0:
            self.positions.pop(symbol, None)
        elif position_direction == 0 or trade_direction == position_direction:
            total_cost = existing["avg_price"] * existing["quantity"] + price * quantity
            avg_price = total_cost / new_quantity
            self.positions[symbol] = {
                "symbol": symbol,
                "quantity": new_quantity,
                "avg_price": avg_price,
                "sector": existing.get("sector") or sector,
            }
        else:
            if (new_direction := (1 if new_quantity > 0 else (-1 if new_quantity < 0 else 0))) == position_direction:
                existing["quantity"] = new_quantity
                self.positions[symbol] = existing
            elif new_direction == 0:
                self.positions.pop(symbol, None)
            else:
                self.positions[symbol] = {
                    "symbol": symbol,
                    "quantity": new_quantity,
                    "avg_price": price,
                    "sector": existing.get("sector") or sector,
                }

        self.cash -= notional

        trade = Trade(
            id=f"{symbol}-{int(datetime.utcnow().timestamp() * 1000)}",
            timestamp=datetime.utcnow().isoformat(),
            symbol=symbol,
            quantity=quantity,
            price=price,
            notional=notional,
            reason=reason,
            strategy=strategy,
            sector=existing.get("sector") or sector,
        )
        self.trades.append(trade)
        logger.debug("Executed portfolio trade", extra={"trade": trade.__dict__})
        return trade.__dict__


__all__ = ["PortfolioService"]
