"""Portfolio accounting with fees and long-only constraints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float


class Portfolio:
    """Track cash, positions, and PnL."""

    def __init__(
        self,
        maker_fee_bps: float,
        taker_fee_bps: float,
        long_only: bool = True,
        initial_cash: float = 1_000_000.0,
    ) -> None:
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.long_only = long_only
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self._marks: Dict[str, float] = {}
        self.realized_pnl = 0.0
        self.fees_paid = 0.0

    def fee_rate(self, liquidity: Literal["maker", "taker"] = "taker") -> float:
        return (self.maker_fee_bps if liquidity == "maker" else self.taker_fee_bps) / 10_000

    def mark_price(self, symbol: str, price: float) -> None:
        self._marks[symbol] = price

    def position(self, symbol: str) -> Position | None:
        return self.positions.get(symbol)

    def total_equity(self) -> float:
        return self.cash + self.current_exposure_value + self.unrealized_pnl

    @property
    def current_exposure_value(self) -> float:
        return sum(pos.quantity * self._marks.get(symbol, pos.avg_price) for symbol, pos in self.positions.items())

    @property
    def unrealized_pnl(self) -> float:
        pnl = 0.0
        for symbol, pos in self.positions.items():
            price = self._marks.get(symbol, pos.avg_price)
            pnl += (price - pos.avg_price) * pos.quantity
        return pnl

    def apply_fill(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: float,
        price: float,
        liquidity: Literal["maker", "taker"] = "taker",
    ) -> dict[str, float]:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        fee_rate = self.fee_rate(liquidity)
        notional = quantity * price
        fee = notional * fee_rate
        self.fees_paid += fee
        position = self.positions.get(symbol)
        if side == "BUY":
            if self.long_only and position and position.quantity < 0:
                raise ValueError("long-only portfolio cannot hold net short")
            self.cash -= notional + fee
            if not position:
                position = Position(symbol=symbol, quantity=quantity, avg_price=price)
            else:
                total_qty = position.quantity + quantity
                position.avg_price = (position.avg_price * position.quantity + price * quantity) / total_qty
                position.quantity = total_qty
            self.positions[symbol] = position
        else:
            if self.long_only and (not position or position.quantity < quantity):
                raise ValueError("sell would create short position")
            self.cash += notional - fee
            realized = (price - position.avg_price) * quantity - fee
            self.realized_pnl += realized
            position.quantity -= quantity
            if position.quantity <= 1e-8:
                self.positions.pop(symbol, None)
            else:
                self.positions[symbol] = position
        self.mark_price(symbol, price)
        return {"notional": notional, "fee": fee, "cash": self.cash, "realized_pnl": self.realized_pnl}

    def exposure_fraction(self, total_equity: float | None = None) -> float:
        equity = total_equity or self.total_equity()
        if equity == 0:
            return 0.0
        return self.current_exposure_value / equity

    def snapshot(self) -> dict[str, float]:
        return {
            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "fees_paid": self.fees_paid,
            "exposure": self.current_exposure_value,
        }
