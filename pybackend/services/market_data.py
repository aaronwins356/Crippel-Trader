"""Synthetic market data generator and analytics pipeline."""

from __future__ import annotations

import asyncio
import math
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..data.seed_assets import SEED_ASSETS
from ..utils.indicators import (
    calculate_bollinger_bands,
    calculate_drawdown,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_volatility,
    normalize_number,
)
from ..utils.logger import get_child
from .integrations.kraken import KrakenMarketDataFeed
from .portfolio import PortfolioService
from .strategy import StrategyService

logger = get_child("market")

EventHandler = Callable[[Any], Awaitable[None] | None]


class MarketDataService:
    HISTORY_LIMIT = 720
    SNAPSHOT_LIMIT = 240

    def __init__(self, interval_ms: int = 2500) -> None:
        self.interval_ms = interval_ms
        self.interval_seconds = interval_ms / 1000
        self.portfolio_service = PortfolioService()
        self.strategy_service = StrategyService(self.portfolio_service)
        self.assets: List[Dict[str, Any]] = [
            {
                **asset,
                "price": asset["basePrice"],
                "lastUpdate": datetime.utcnow().isoformat(),
                "change": 0.0,
                "changePercent": 0.0,
                "volume": 0.0,
            }
            for asset in SEED_ASSETS
        ]
        self.history: Dict[str, List[Dict[str, float]]] = {}
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self._listeners: Dict[str, List[EventHandler]] = defaultdict(list)
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._asset_lookup: Dict[str, Dict[str, Any]] = {
            asset["symbol"]: asset for asset in self.assets
        }
        self._kraken_pairs = self._build_kraken_pairs()
        self._kraken_symbols = set(self._kraken_pairs.values())
        self._kraken_feed: Optional[KrakenMarketDataFeed] = None
        self._kraken_task: Optional[asyncio.Task] = None
        self._kraken_enabled = False
        self._kraken_candle_state: Dict[str, Dict[str, Any]] = {}
        self._kraken_volume_totals: Dict[str, float] = {}
        self._kraken_last_broadcast: Dict[str, datetime] = {}

        for asset in self.assets:
            self.history[asset["symbol"]] = self.generate_seed_history(asset)

        self.rebuild_snapshots()
        # Prime the analytics so REST calls have immediate data.
        self.tick(initial=True)

    def on(self, event: str, handler: EventHandler) -> None:
        self._listeners[event].append(handler)

    def off(self, event: str, handler: EventHandler) -> None:
        if handler in self._listeners.get(event, []):
            self._listeners[event].remove(handler)

    def _emit(self, event: str, payload: Any) -> None:
        if not self._loop:
            return
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        for handler in list(self._listeners.get(event, [])):
            try:
                result = handler(payload)
                if asyncio.iscoroutine(result):
                    if running_loop and running_loop is self._loop:
                        asyncio.create_task(result)
                    else:
                        asyncio.run_coroutine_threadsafe(result, self._loop)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Event handler failure", exc_info=exc)

    async def start(self) -> None:
        if self._task:
            return
        self._loop = asyncio.get_running_loop()
        self._running = True
        if self._kraken_pairs and not self._kraken_task:
            self._kraken_feed = KrakenMarketDataFeed(
                list(self._kraken_pairs.keys()),
                self._handle_kraken_ticker,
            )
            self._kraken_enabled = bool(self._kraken_pairs)
            self._kraken_task = asyncio.create_task(self._run_kraken_feed())
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        if self._kraken_task:
            if self._kraken_feed:
                await self._kraken_feed.stop()
            self._kraken_task.cancel()
            try:
                await self._kraken_task
            except asyncio.CancelledError:
                pass
            self._kraken_task = None
            self._kraken_feed = None
        self._kraken_enabled = False
        for symbol, state in list(self._kraken_candle_state.items()):
            try:
                self._finalize_kraken_candle(symbol, state)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to finalize Kraken candle", exc_info=exc)
        self._kraken_candle_state.clear()
        self._kraken_volume_totals.clear()
        self._kraken_last_broadcast.clear()
        self._loop = None

    async def _run(self) -> None:
        while self._running:
            start = time.perf_counter()
            self.tick()
            elapsed = time.perf_counter() - start
            await asyncio.sleep(max(0.0, self.interval_seconds - elapsed))

    async def _run_kraken_feed(self) -> None:
        if not self._kraken_feed:
            return
        try:
            await self._kraken_feed.run()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Kraken market data feed terminated", exc_info=exc)
        finally:
            self._kraken_enabled = False

    def rebuild_snapshots(self) -> None:
        self.snapshots = {
            asset["symbol"]: {
                "symbol": asset["symbol"],
                "price": asset["price"],
                "sector": asset["sector"],
                "name": asset["name"],
            }
            for asset in self.assets
        }
        self._asset_lookup = {asset["symbol"]: asset for asset in self.assets}

    def generate_seed_history(self, asset: Dict[str, Any]) -> List[Dict[str, float]]:
        candles: List[Dict[str, float]] = []
        price = asset["basePrice"]
        now = datetime.utcnow()
        for index in range(self.SNAPSHOT_LIMIT):
            timestamp = (now - timedelta(minutes=self.SNAPSHOT_LIMIT - index)).isoformat()
            drift = price * 0.0008 * math.sin(index / 12)
            variance = price * 0.012
            shock = (random.random() - 0.5) * variance
            open_price = price
            close = max(0.1, open_price + drift + shock)
            high = max(open_price, close) + random.random() * variance * 0.5
            low = min(open_price, close) - random.random() * variance * 0.5
            volume = abs((variance + shock) * 40)
            candles.append(
                {
                    "timestamp": timestamp,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
            )
            price = close
        return candles

    def _build_kraken_pairs(self) -> Dict[str, str]:
        pairs: Dict[str, str] = {}
        for asset in self.assets:
            pair = self._kraken_pair_for_symbol(asset["symbol"])
            if pair:
                pairs[pair] = asset["symbol"]
        return pairs

    @staticmethod
    def _kraken_pair_for_symbol(symbol: str) -> Optional[str]:
        mapping = {
            "BTC-USD": "XBT/USD",
        }
        if symbol in mapping:
            return mapping[symbol]
        if "-" in symbol:
            base, quote = symbol.split("-", 1)
            return f"{base}/{quote}"
        return None

    def _finalize_kraken_candle(self, symbol: str, state: Dict[str, Any]) -> None:
        candles = self.history.setdefault(symbol, [])
        candle = {
            "timestamp": (state["bucket"] + timedelta(minutes=1)).isoformat(),
            "open": state["open"],
            "high": state["high"],
            "low": state["low"],
            "close": state["close"],
            "volume": max(state.get("volume", 0.0), 0.0),
        }
        candles.append(candle)
        if len(candles) > self.HISTORY_LIMIT:
            candles.pop(0)

    def _handle_kraken_ticker(self, pair: str, payload: Dict[str, Any]) -> None:
        symbol = self._kraken_pairs.get(pair)
        if not symbol:
            return
        asset = self._asset_lookup.get(symbol)
        if not asset:
            return
        price_data = payload.get("c") or []
        try:
            price = float(price_data[0])
        except (IndexError, TypeError, ValueError):
            return

        previous_price = float(asset.get("price") or price)
        now = datetime.utcnow()
        change = price - previous_price
        change_percent = 0.0 if previous_price == 0 else (change / previous_price) * 100

        volume_values = payload.get("v") or []
        try:
            volume_total = float(volume_values[0])
        except (IndexError, TypeError, ValueError):
            volume_total = 0.0
        previous_total = self._kraken_volume_totals.get(symbol)
        volume_delta = 0.0 if previous_total is None else max(volume_total - previous_total, 0.0)
        self._kraken_volume_totals[symbol] = volume_total

        asset["price"] = normalize_number(price, 4)
        asset["lastUpdate"] = now.isoformat()
        asset["change"] = normalize_number(change, 4)
        asset["changePercent"] = normalize_number(change_percent, 2)
        asset["volume"] = normalize_number(volume_delta, 2)

        bucket = now.replace(second=0, microsecond=0)
        state = self._kraken_candle_state.get(symbol)
        if not state or state["bucket"] != bucket:
            if state:
                self._finalize_kraken_candle(symbol, state)
            state = {
                "bucket": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume_delta,
            }
            self._kraken_candle_state[symbol] = state
        else:
            state["close"] = price
            state["high"] = max(state["high"], price)
            state["low"] = min(state["low"], price)
            state["volume"] += volume_delta

        if symbol in self.snapshots:
            self.snapshots[symbol]["price"] = asset["price"]

        candles = self.history.setdefault(symbol, [])
        trade = self.strategy_service.process(symbol, candles, asset)
        if trade:
            self._emit("trade", trade)

        self._kraken_enabled = True

        last_broadcast = self._kraken_last_broadcast.get(symbol)
        if not last_broadcast or (now - last_broadcast).total_seconds() >= 1.0:
            self._kraken_last_broadcast[symbol] = now
            self.broadcast()

    def tick(self, initial: bool = False) -> None:
        try:
            for asset in self.assets:
                symbol = asset["symbol"]
                if self._kraken_enabled and symbol in self._kraken_symbols:
                    continue
                candles = self.history.get(symbol, [])
                previous = candles[-1] if candles else {
                    "close": asset["basePrice"],
                    "volume": 0.0,
                    "timestamp": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
                }
                drift = previous["close"] * (0.0012 * math.sin(time.time() / 60))
                volatility = previous["close"] * (0.0025 + random.random() * 0.003)
                shock = (random.random() - 0.5) * volatility
                open_price = previous["close"]
                close = max(0.1, open_price + drift + shock)
                high = max(open_price, close) + random.random() * volatility
                low = min(open_price, close) - random.random() * volatility
                volume = abs(shock) * 100 + random.random() * 250
                candle = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
                candles.append(candle)
                if len(candles) > self.HISTORY_LIMIT:
                    candles.pop(0)

                previous_price = float(asset.get("price") or close)
                change = close - previous_price
                change_percent = 0.0 if previous_price == 0 else (change / previous_price) * 100

                asset["price"] = normalize_number(close, 4)
                asset["lastUpdate"] = candle["timestamp"]
                asset["change"] = normalize_number(change, 4)
                asset["changePercent"] = normalize_number(change_percent, 2)
                asset["volume"] = normalize_number(volume, 2)

                trade = self.strategy_service.process(symbol, candles, asset)
                if trade:
                    self._emit("trade", trade)

            self.rebuild_snapshots()
            self.broadcast()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Market tick failed", exc_info=exc)
            self._emit("error", exc)
        finally:
            if initial:
                self._loop = self._loop  # no-op to satisfy coverage instrumentation

    def get_portfolio(self) -> Dict[str, Any]:
        return self.portfolio_service.get_state(self.snapshots)

    def get_orders(self) -> List[Dict[str, Any]]:
        return self.get_portfolio()["trades"]

    def get_history(self, symbol: str) -> List[Dict[str, Any]]:
        return list(self.history.get(symbol, []))

    def get_analytics(self) -> Dict[str, Any]:
        analytics = []
        for asset in self.assets:
            symbol = asset["symbol"]
            candles = self.history.get(symbol, [])
            closes = [candle["close"] for candle in candles]
            bollinger = calculate_bollinger_bands(closes, 20, 2)
            macd = calculate_macd(closes, 12, 26, 9)
            analytics.append(
                {
                    "symbol": symbol,
                    "name": asset["name"],
                    "sector": asset["sector"],
                    "class": asset["class"],
                    "price": asset["price"],
                    "changePercent": asset["changePercent"],
                    "sma21": calculate_sma(closes, 21),
                    "sma50": calculate_sma(closes, 50),
                    "ema21": calculate_ema(closes, 21),
                    "ema100": calculate_ema(closes, 100),
                    "rsi": calculate_rsi(closes, 14),
                    "macd": macd,
                    "bollinger": bollinger,
                    "volatility": calculate_volatility(closes, 30),
                    "drawdown": calculate_drawdown(closes[-180:]),
                    "latestCandle": candles[-1] if candles else None,
                }
            )

        sorted_assets = sorted(analytics, key=lambda item: item.get("changePercent") or 0, reverse=True)
        leaders = sorted_assets[:3]
        laggards = list(reversed(sorted_assets[-3:]))
        risk_buckets = {"veryHigh": [], "high": [], "medium": [], "low": []}
        for asset in analytics:
            vol = asset.get("volatility") or 0
            if vol >= 80:
                risk_buckets["veryHigh"].append(asset)
            elif vol >= 40:
                risk_buckets["high"].append(asset)
            elif vol >= 20:
                risk_buckets["medium"].append(asset)
            else:
                risk_buckets["low"].append(asset)

        return {
            "assets": analytics,
            "leaders": leaders,
            "laggards": laggards,
            "riskBuckets": risk_buckets,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_strategy_log(self) -> List[Dict[str, Any]]:
        return self.strategy_service.get_log()

    def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        symbol = order.get("symbol")
        if not symbol:
            raise ValueError("Unknown symbol")
        asset = next((item for item in self.assets if item["symbol"] == symbol), None)
        if not asset:
            raise ValueError(f"Unknown symbol {symbol}")
        quantity_value = order.get("quantity")
        if quantity_value is None:
            raise ValueError("Quantity required")

        trade = self.portfolio_service.apply_trade(
            symbol=symbol,
            quantity=float(quantity_value),
            price=float(order.get("price", asset["price"])),
            reason=order.get("reason", "manual-override"),
            strategy=order.get("strategy", "manual"),
            sector=asset.get("sector"),
        )
        self.rebuild_snapshots()
        self.broadcast()
        self._emit("trade", trade)
        return trade

    def broadcast(self) -> None:
        payload = {
            "type": "market:update",
            "market": self.assets,
            "analytics": self.get_analytics(),
            "portfolio": self.get_portfolio(),
            "strategy": {"log": self.get_strategy_log()},
        }
        self._emit("update", payload)


__all__ = ["MarketDataService"]
