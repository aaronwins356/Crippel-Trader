"""Enhanced Kraken exchange adapter with crypto and stock support."""
from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import httpx
import structlog
import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..config import get_settings
from ..models.core import Order, PriceTick
from ..notifications import get_notification_service
from .base import ExchangeAdapter

KRAKEN_WS_URL = "wss://ws.kraken.com"
KRAKEN_REST_URL = "https://api.kraken.com/0/public"
KRAKEN_PRIVATE_URL = "https://api.kraken.com/0/private"

# Kraken symbol mappings
CRYPTO_SYMBOL_MAP = {
    "BTC/USD": "XBTUSD",
    "ETH/USD": "ETHUSD", 
    "ADA/USD": "ADAUSD",
    "SOL/USD": "SOLUSD",
    "MATIC/USD": "MATICUSD",
    "DOT/USD": "DOTUSD",
    "LINK/USD": "LINKUSD",
    "UNI/USD": "UNIUSD",
    "AAVE/USD": "AAVEUSD",
    "ATOM/USD": "ATOMUSD",
}

STOCK_SYMBOL_MAP = {
    "TSLA": "TSLA/USD",
    "AAPL": "AAPL/USD", 
    "GOOGL": "GOOGL/USD",
    "MSFT": "MSFT/USD",
    "AMZN": "AMZN/USD",
    "NVDA": "NVDA/USD",
    "META": "META/USD",
    "SPY": "SPY/USD",
    "QQQ": "QQQ/USD",
    "IWM": "IWM/USD",
    "GLD": "GLD/USD",
    "TLT": "TLT/USD",
}


@dataclass
class KrakenAdapter(ExchangeAdapter):
    """Enhanced adapter for interacting with Kraken crypto and stock markets."""

    session: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=30))
    ws: Optional[WebSocketClientProtocol] = None
    _subscribed_symbols: Set[str] = field(default_factory=set)
    _reconnect_attempts: int = 0
    _max_reconnect_attempts: int = 5
    _reconnect_delay: float = 5.0
    _last_heartbeat: float = 0.0
    _heartbeat_interval: float = 30.0

    def __init__(self) -> None:
        self.session = httpx.AsyncClient(timeout=30)
        self.ws = None
        self._subscribed_symbols = set()
        self._reconnect_attempts = 0
        self._logger = structlog.get_logger(__name__)
        self._settings = get_settings()
        self._notification_service = get_notification_service()
        self._last_heartbeat = time.time()

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol format to Kraken format."""
        if symbol in CRYPTO_SYMBOL_MAP:
            return CRYPTO_SYMBOL_MAP[symbol]
        elif symbol in STOCK_SYMBOL_MAP:
            return STOCK_SYMBOL_MAP[symbol]
        else:
            # Try to handle other formats
            return symbol.replace("/", "").replace("-", "")
    
    def _denormalize_symbol(self, kraken_symbol: str) -> str:
        """Convert Kraken symbol back to standard format."""
        # Reverse lookup in mappings
        for standard, kraken in CRYPTO_SYMBOL_MAP.items():
            if kraken == kraken_symbol:
                return standard
        for standard, kraken in STOCK_SYMBOL_MAP.items():
            if kraken == kraken_symbol:
                return standard
        return kraken_symbol

    async def connect_market_data(self, symbols: list[str]) -> AsyncIterator[PriceTick]:
        """Connect to Kraken WebSocket and stream market data."""
        normalized_symbols = [self._normalize_symbol(symbol) for symbol in symbols]
        self._subscribed_symbols.update(normalized_symbols)
        
        while True:
            try:
                await self._ensure_ws_connection()
                if self.ws is None:
                    raise RuntimeError("WebSocket connection failed")
                
                # Subscribe to ticker data
                subscribe_msg = {
                    "event": "subscribe",
                    "pair": normalized_symbols,
                    "subscription": {"name": "ticker"}
                }
                
                await self.ws.send(json.dumps(subscribe_msg))
                self._logger.info("Subscribed to market data", symbols=normalized_symbols)
                
                # Send initial system notification
                await self._notification_service.send_system_alert(
                    "Market Data Connected",
                    f"Successfully connected to Kraken WebSocket for {len(symbols)} symbols",
                    "success"
                )
                
                async for message in self.ws:
                    try:
                        if not isinstance(message, str):
                            continue
                            
                        data = json.loads(message)
                        
                        # Handle heartbeat
                        if isinstance(data, dict):
                            if data.get("event") == "heartbeat":
                                self._last_heartbeat = time.time()
                                continue
                            elif data.get("event") == "systemStatus":
                                status = data.get("status", "unknown")
                                self._logger.info("Kraken system status", status=status)
                                continue
                            elif data.get("event") == "subscriptionStatus":
                                self._logger.info("Subscription status", data=data)
                                continue
                        
                        # Handle ticker data
                        if isinstance(data, list) and len(data) >= 4:
                            channel_id, ticker_data, channel_name, pair = data[:4]
                            
                            if channel_name == "ticker" and isinstance(ticker_data, dict):
                                try:
                                    # Extract price and volume data
                                    ask_price = float(ticker_data.get("a", [0.0])[0])
                                    bid_price = float(ticker_data.get("b", [0.0])[0])
                                    last_price = float(ticker_data.get("c", [0.0])[0])
                                    volume = float(ticker_data.get("v", [0.0])[0])
                                    
                                    # Use last price, fallback to mid price
                                    price = last_price if last_price > 0 else (ask_price + bid_price) / 2
                                    
                                    if price > 0:
                                        standard_symbol = self._denormalize_symbol(pair)
                                        tick = PriceTick(
                                            symbol=standard_symbol,
                                            price=price,
                                            volume=volume,
                                            ts=datetime.utcnow(),
                                            bid=bid_price,
                                            ask=ask_price
                                        )
                                        yield tick
                                        
                                except (ValueError, IndexError, KeyError) as e:
                                    self._logger.warning("Error parsing ticker data", error=str(e), data=ticker_data)
                                    continue
                    
                    except json.JSONDecodeError as e:
                        self._logger.warning("Invalid JSON received", error=str(e), message=message)
                        continue
                    except Exception as e:
                        self._logger.error("Error processing message", error=str(e), message=message)
                        continue
                        
            except (ConnectionClosed, WebSocketException) as e:
                self._logger.warning("WebSocket connection lost", error=str(e))
                await self._handle_reconnection()
                continue
            except Exception as e:
                self._logger.error("Unexpected error in market data stream", error=str(e))
                await self._notification_service.send_system_alert(
                    "Market Data Error",
                    f"Unexpected error: {str(e)}",
                    "error"
                )
                await asyncio.sleep(self._reconnect_delay)
                continue

    async def submit_order(self, order: Order) -> None:
        """Submit an order to Kraken (live trading mode only)."""
        if self._settings.trading_mode == "paper":
            self._logger.info("Paper trading mode - order not submitted to exchange", order=order)
            return
            
        if not self._settings.kraken_api_key or not self._settings.kraken_api_secret:
            raise RuntimeError("Kraken API credentials not configured for live trading")
        
        normalized_symbol = self._normalize_symbol(order.symbol)
        
        payload = {
            "pair": normalized_symbol,
            "type": order.side.value.lower(),
            "ordertype": order.type.value.lower(),
            "volume": str(order.size),
        }
        
        if order.price:
            payload["price"] = str(order.price)
        
        try:
            response = await self._signed_post("/AddOrder", payload)
            self._logger.info("Order submitted successfully", order=order, response=response)
            
            await self._notification_service.send_trade_alert(
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.size,
                price=order.price or 0.0,
                strategy="Live Trading"
            )
            
        except Exception as e:
            self._logger.error("Failed to submit order", order=order, error=str(e))
            await self._notification_service.send_system_alert(
                "Order Submission Failed",
                f"Failed to submit {order.side.value} order for {order.symbol}: {str(e)}",
                "error"
            )
            raise

    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance from Kraken."""
        if self._settings.trading_mode == "paper":
            return {"USD": self._settings.initial_capital}
            
        try:
            response = await self._signed_post("/Balance", {})
            return response.get("result", {})
        except Exception as e:
            self._logger.error("Failed to get account balance", error=str(e))
            return {}

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get open positions from Kraken."""
        if self._settings.trading_mode == "paper":
            return []
            
        try:
            response = await self._signed_post("/OpenPositions", {})
            return list(response.get("result", {}).values())
        except Exception as e:
            self._logger.error("Failed to get open positions", error=str(e))
            return []

    async def _ensure_ws_connection(self) -> None:
        """Ensure WebSocket connection is established."""
        if self.ws and not self.ws.closed:
            # Check if connection is still alive
            current_time = time.time()
            if current_time - self._last_heartbeat > self._heartbeat_interval * 2:
                self._logger.warning("WebSocket heartbeat timeout, reconnecting")
                await self._close_ws()
            else:
                return
        
        try:
            self._logger.info("Establishing Kraken WebSocket connection")
            self.ws = await websockets.connect(
                self._settings.kraken_ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self._last_heartbeat = time.time()
            self._reconnect_attempts = 0
            self._logger.info("Kraken WebSocket connected successfully")
            
        except Exception as e:
            self._logger.error("Failed to connect to Kraken WebSocket", error=str(e))
            raise

    async def _handle_reconnection(self) -> None:
        """Handle WebSocket reconnection with exponential backoff."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            error_msg = f"Max reconnection attempts ({self._max_reconnect_attempts}) exceeded"
            self._logger.error(error_msg)
            await self._notification_service.send_system_alert(
                "Connection Failed",
                error_msg,
                "error"
            )
            raise RuntimeError(error_msg)
        
        self._reconnect_attempts += 1
        delay = self._reconnect_delay * (2 ** (self._reconnect_attempts - 1))  # Exponential backoff
        
        self._logger.info(
            "Attempting to reconnect",
            attempt=self._reconnect_attempts,
            delay=delay
        )
        
        await self._close_ws()
        await asyncio.sleep(delay)

    async def _close_ws(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                self._logger.warning("Error closing WebSocket", error=str(e))
            finally:
                self.ws = None

    async def _signed_post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a signed POST request to Kraken API."""
        if not self._settings.kraken_api_key or not self._settings.kraken_api_secret:
            raise RuntimeError("Kraken API credentials not configured")
        
        # Note: This is a simplified implementation
        # In production, you would need proper HMAC-SHA512 signing
        headers = {
            "API-Key": self._settings.kraken_api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = await self.session.post(
            f"{KRAKEN_PRIVATE_URL}{path}",
            data=data,
            headers=headers
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("error"):
            raise RuntimeError(f"Kraken API error: {result['error']}")
        
        return result

    async def close(self) -> None:
        """Close all connections."""
        await self._close_ws()
        await self.session.aclose()
        self._logger.info("Kraken adapter closed")
