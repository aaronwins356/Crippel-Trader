from __future__ import annotations

from datetime import datetime

import pytest

from crippel.engine.fills import PaperFillModel
from crippel.models.core import Order
from crippel.models.enums import Mode, OrderSide, OrderType


def make_order(order_type: OrderType) -> Order:
    return Order(
        id="1",
        symbol="XBT/USD",
        side=OrderSide.BUY,
        type=order_type,
        size=1.0,
        price=100.0,
        ts=datetime.utcnow(),
        mode=Mode.PAPER,
        aggression=5,
    )


def test_paper_fill_maker_fee() -> None:
    model = PaperFillModel(maker_fee_bps=1.0, taker_fee_bps=2.0)
    order = make_order(OrderType.LIMIT)
    fill = model.fill(order, price=100.0)
    assert fill.maker is True
    assert fill.fee == pytest.approx(0.01, rel=1e-6)


def test_paper_fill_taker_fee() -> None:
    model = PaperFillModel(maker_fee_bps=1.0, taker_fee_bps=2.0)
    order = make_order(OrderType.MARKET)
    fill = model.fill(order, price=200.0)
    assert fill.maker is False
    assert fill.fee == pytest.approx(0.04, rel=1e-6)
