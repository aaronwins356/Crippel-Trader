"""Enum definitions for trading primitives."""
from __future__ import annotations

from enum import Enum


class Mode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class SignalType(str, Enum):
    FLAT = "flat"
    LONG = "long"
    SHORT = "short"


class AggressionLevel(int, Enum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5
    LEVEL_6 = 6
    LEVEL_7 = 7
    LEVEL_8 = 8
    LEVEL_9 = 9
    LEVEL_10 = 10


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
