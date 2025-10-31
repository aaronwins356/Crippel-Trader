from datetime import datetime, timezone

import pytest

from croc.config import RiskLimits, TradingMode
from croc.models.types import Fill, Order, OrderType, Side
from croc.risk.risk_manager import RiskError, RiskManager


def make_order(size: float, price: float) -> Order:
    return Order(
        id="test-1",
        symbol="BTC/USDT",
        side=Side.BUY,
        size=size,
        price=price,
        order_type=OrderType.MARKET,
        mode=TradingMode.PAPER,
    )


def make_fill(size: float, price: float, side: Side = Side.BUY) -> Fill:
    return Fill(
        order_id="test-1",
        symbol="BTC/USDT",
        side=side,
        size=size,
        price=price,
        fee=0.0,
        timestamp=datetime.now(tz=timezone.utc),
    )


def test_position_limit_enforced():
    limits = RiskLimits(max_position=1.0, max_notional=10_000.0, max_daily_drawdown=1000.0)
    manager = RiskManager(limits)
    order = make_order(size=2.0, price=25_000)
    with pytest.raises(RiskError):
        manager.check_order(order, price=25_000)


def test_drawdown_triggers_kill_switch():
    limits = RiskLimits(max_position=5.0, max_notional=1_000_000.0, max_daily_drawdown=10.0)
    manager = RiskManager(limits)
    manager.update_fill(make_fill(1.0, 10.0, Side.BUY))
    manager.update_fill(
        Fill(
            order_id="test-2",
            symbol="BTC/USDT",
            side=Side.SELL,
            size=1.0,
            price=0.0,
            fee=0.0,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    assert manager.state.kill_switch
    with pytest.raises(RiskError):
        manager.check_order(make_order(0.1, 10.0), price=10.0)
