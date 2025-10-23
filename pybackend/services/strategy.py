"""MACD/RSI based trading strategy implemented in Python."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..utils.indicators import calculate_ema, calculate_macd, calculate_rsi
from ..utils.logger import get_child

logger = get_child("strategy")


class StrategyService:
    def __init__(self, portfolio_service) -> None:
        self.portfolio_service = portfolio_service
        self.log: List[Dict[str, object]] = []
        self.last_signals: Dict[str, Dict[str, float]] = {}

    def record(self, event: Dict[str, object]) -> None:
        self.log.append(event)
        if len(self.log) > 300:
            self.log.pop(0)
        logger.debug("Strategy event", extra={"event": event})

    def get_log(self) -> List[Dict[str, object]]:
        return list(reversed(self.log))

    def get_position(self, symbol: str) -> Dict[str, float]:
        return self.portfolio_service.positions.get(symbol, {"quantity": 0.0, "avg_price": 0.0})

    def process(self, symbol: str, candles: List[Dict[str, float]], meta: Optional[Dict[str, object]]) -> Optional[Dict[str, object]]:
        if not candles:
            return None
        closes = [candle["close"] for candle in candles]
        if len(closes) < 35:
            return None

        price = closes[-1]
        rsi = calculate_rsi(closes, 14)
        ema_fast = calculate_ema(closes, 21)
        ema_slow = calculate_ema(closes, 55)
        macd = calculate_macd(closes, 12, 26, 9)

        if not all([rsi, ema_fast, ema_slow, macd]):
            return None

        last_histogram = self.last_signals.get(symbol, {}).get("histogram", macd["histogram"])
        histogram_slope = macd["histogram"] - last_histogram
        signal = {
            "symbol": symbol,
            "timestamp": candles[-1]["timestamp"],
            "price": price,
            "rsi": rsi,
            "emaFast": ema_fast,
            "emaSlow": ema_slow,
            "macd": macd["macd"],
            "macdSignal": macd["signal"],
            "histogram": macd["histogram"],
            "histogramSlope": histogram_slope,
        }

        position = self.get_position(symbol)
        base_risk = max(1, round((self.portfolio_service.initial_capital * 0.02) / price))
        action: Optional[str] = None
        quantity = 0.0

        if macd["histogram"] > 0 and histogram_slope >= 0 and rsi <= 70 and price > ema_fast:
            if position["quantity"] <= 0:
                action = "BUY"
                quantity = abs(position["quantity"]) + base_risk if position["quantity"] < 0 else base_risk
        elif macd["histogram"] <= 0.1 and histogram_slope <= 0 and rsi >= 40 and price < ema_fast:
            if position["quantity"] > 0:
                action = "SELL"
                quantity = -min(position["quantity"], base_risk)
        elif rsi < 28 and position["quantity"] <= 0:
            action = "BUY"
            quantity = base_risk
        elif rsi > 72 and position["quantity"] > 0:
            action = "SELL"
            quantity = -min(position["quantity"], base_risk)

        self.last_signals[symbol] = {"histogram": macd["histogram"], "timestamp": signal["timestamp"]}

        if not action or quantity == 0:
            return None

        trade = self.portfolio_service.apply_trade(
            symbol=symbol,
            quantity=quantity,
            price=price,
            reason="signal-long" if action == "BUY" else "signal-exit",
            strategy="MACD-RSI",
            sector=(meta or {}).get("sector"),
        )
        event = {**signal, "action": action, "quantity": quantity, "tradeId": trade["id"]}
        self.record(event)
        return trade


__all__ = ["StrategyService"]
