from __future__ import annotations

from datetime import datetime

from crippel.engine.portfolio import Portfolio
from crippel.models.core import Fill
from crippel.models.enums import Mode, OrderSide


def test_portfolio_updates_with_fill() -> None:
    portfolio = Portfolio(starting_cash=1000.0, mode=Mode.PAPER)
    fill = Fill(
        order_id="1",
        symbol="XBT/USD",
        side=OrderSide.BUY,
        size=1.0,
        price=100.0,
        fee=0.1,
        ts=datetime.utcnow(),
        maker=True,
    )
    portfolio.update_fill(fill)
    portfolio.mark_price("XBT/USD", 110.0)
    snapshot = portfolio.snapshot(datetime.utcnow())
    assert snapshot.cash < 1000.0
    assert snapshot.pnl_unrealized > 0
    assert snapshot.positions["XBT/USD"].size == 1.0
