"""FastAPI application exposing the trading simulator services."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from .services import (
    LiveTradingService,
    MarketDataService,
    TradingModeService,
)
from .services.websocket_manager import WebSocketManager
from .utils.logger import get_child

logger = get_child("server")

app = FastAPI(title="Crippel Trader Backend", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

market_data_service = MarketDataService()
live_trading_service = LiveTradingService()
trading_mode_service = TradingModeService(market_data_service, live_trading_service)
ws_manager = WebSocketManager()

market_data_service.on("update", ws_manager.dispatch)
market_data_service.on("trade", lambda trade: ws_manager.dispatch({"type": "strategy:trade", "trade": trade}))
live_trading_service.on("update", ws_manager.dispatch)
trading_mode_service.on("mode:change", ws_manager.dispatch)


@app.on_event("startup")
async def startup() -> None:
    await market_data_service.start()
    await live_trading_service.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    await market_data_service.stop()
    await live_trading_service.stop()


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/modes")
async def get_modes() -> Dict[str, Any]:
    return {
        "current": trading_mode_service.get_mode(),
        "available": trading_mode_service.get_available_modes(),
    }


@app.post("/api/modes")
async def set_mode(payload: Dict[str, Any]) -> Dict[str, Any]:
    mode = payload.get("mode")
    if not mode:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode is required")
    try:
        updated = trading_mode_service.set_mode(mode)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"mode": updated}


def ensure_paper_mode() -> None:
    if not trading_mode_service.is_paper_mode():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Endpoint available only in paper trading mode")


@app.get("/api/assets")
async def get_assets() -> Dict[str, Any]:
    ensure_paper_mode()
    return {"assets": market_data_service.assets}


@app.get("/api/analytics")
async def get_analytics() -> Dict[str, Any]:
    ensure_paper_mode()
    return market_data_service.get_analytics()


@app.get("/api/portfolio")
async def get_portfolio() -> Dict[str, Any]:
    ensure_paper_mode()
    return market_data_service.get_portfolio()


@app.get("/api/orders")
async def get_orders() -> Dict[str, Any]:
    ensure_paper_mode()
    return {"trades": market_data_service.get_orders()}


@app.get("/api/history/{symbol}")
async def get_history(symbol: str) -> Dict[str, Any]:
    ensure_paper_mode()
    return {"symbol": symbol, "candles": market_data_service.get_history(symbol)}


@app.get("/api/strategy/log")
async def get_strategy_log() -> Dict[str, Any]:
    ensure_paper_mode()
    return {"log": market_data_service.get_strategy_log()}


@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
async def post_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_paper_mode()
    try:
        trade = market_data_service.place_order(payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return trade


@app.get("/api/live/state")
async def get_live_state() -> Dict[str, Any]:
    return {"mode": trading_mode_service.get_mode(), "state": live_trading_service.get_state()}


@app.post("/api/live/trades", status_code=status.HTTP_201_CREATED)
async def post_live_trade(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not trading_mode_service.is_live_mode():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Live trading mode must be active to submit trades")
    try:
        trade = await live_trading_service.submit_worker_trade(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return trade


@app.post("/api/live/research", status_code=status.HTTP_201_CREATED)
async def post_live_research(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not trading_mode_service.is_live_mode():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Live trading mode must be active to submit research")
    return live_trading_service.add_research_insight(payload)


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "mode:change", "mode": trading_mode_service.get_mode()})
        if trading_mode_service.is_live_mode():
            await websocket.send_json({"type": "live:update", "state": live_trading_service.get_state()})
        else:
            await websocket.send_json(
                {
                    "type": "market:update",
                    "market": market_data_service.assets,
                    "analytics": market_data_service.get_analytics(),
                    "portfolio": market_data_service.get_portfolio(),
                    "strategy": {"log": market_data_service.get_strategy_log()},
                }
            )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("WebSocket connection error", exc_info=exc)
        await ws_manager.disconnect(websocket)


__all__ = ["app", "market_data_service", "live_trading_service", "trading_mode_service", "ws_manager"]
