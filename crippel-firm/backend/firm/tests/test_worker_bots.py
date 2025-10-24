import asyncio

import pytest

from firm.bots.analyst_bot import AnalystBot
from firm.bots.research_bot import ResearchBot, ResearchConfig
from firm.bots.trader_bot import TraderBot, TraderConfig
from firm.config import FirmConfig
from firm.engine.kraken_adapter import KrakenAdapter
from firm.engine.portfolio import Portfolio
from firm.engine.simulator import SimulatedMarketData
from firm.eventbus import EventBus
from firm.utils.metrics import PerformanceLedger


@pytest.mark.asyncio
async def test_research_bot_generates_ideas():
    config = FirmConfig()
    event_bus = EventBus()
    ledger = PerformanceLedger()
    bot = ResearchBot(event_bus, ledger, ResearchConfig(settings=config.research))
    await bot.start()
    await asyncio.sleep(0.1)
    metrics = await bot.on_evaluate()
    assert metrics["coverage"] >= 0
    await bot.stop()


@pytest.mark.asyncio
async def test_trader_bot_executes_signal():
    event_bus = EventBus()
    ledger = PerformanceLedger()
    market = SimulatedMarketData()
    adapter = KrakenAdapter()
    portfolio = Portfolio(cash=100_000)
    trader = TraderBot(event_bus, ledger, portfolio, adapter, market, TraderConfig())
    analyst_signal = {"bot_id": "analyst", "strength": 0.5, "symbol": "BTC/USD"}
    queue = await event_bus.subscribe("signals")
    await trader.start()
    await event_bus.publish("signals", analyst_signal)
    await asyncio.sleep(0.1)
    metrics = await trader.on_evaluate()
    assert "pnl" in metrics
    await trader.stop()
