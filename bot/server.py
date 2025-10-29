"""FastAPI application exposing trading endpoints and serving static UI."""

from __future__ import annotations

import asyncio
import io
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config_loader import ConfigResult, load_config, redact_config
from .state import BotState
from .trading_engine import TradingEngine, TradingError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = PROJECT_ROOT
CONFIG_PATH = PROJECT_ROOT / "config.json"
LOG_DIR = PROJECT_ROOT / "logs"

app = FastAPI(title="Croc-Bot Trading System", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = BotState(balance=0)
engine: TradingEngine | None = None
config_result: ConfigResult | None = None


@app.on_event("startup")
async def startup_event() -> None:
    global config_result, engine, state
    config_result = load_config(CONFIG_PATH)
    if config_result.config:
        cfg = config_result.config
        state = BotState(balance=cfg.trading.capital)
        engine = TradingEngine(cfg, state, LOG_DIR)
    else:
        state = BotState(balance=0)


@app.get("/")
async def root() -> FileResponse:
    index_path = STATIC_ROOT / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.get("/config")
async def get_config() -> JSONResponse:
    if not config_result:
        raise HTTPException(status_code=500, detail="Configuration not loaded")
    if config_result.errors:
        return JSONResponse({"errors": [asdict(err) for err in config_result.errors]}, status_code=400)
    assert config_result.config is not None
    return JSONResponse({"config": redact_config(config_result.config)})


@app.post("/trade")
async def place_trade(payload: Dict[str, Any]) -> JSONResponse:
    if not engine:
        raise HTTPException(status_code=400, detail="Engine not ready")
    if config_result and config_result.config and config_result.config.runtime.read_only:
        raise HTTPException(status_code=403, detail="Trading disabled in read-only mode")

    required = {"symbol", "side", "size", "price"}
    if not required.issubset(payload):
        missing = required - payload.keys()
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing)}")

    try:
        trade = engine.submit_order(
            symbol=str(payload["symbol"]),
            side=str(payload["side"]),
            size=float(payload["size"]),
            price=float(payload["price"]),
            taker=bool(payload.get("taker", True)),
        )
    except TradingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse({"trade": {
        "timestamp": trade.timestamp.isoformat(),
        "symbol": trade.symbol,
        "side": trade.side,
        "size": trade.size,
        "price": trade.price,
        "fee": trade.fee,
        "total_cost": trade.total_cost,
    }})


@app.get("/export")
async def export_artifacts() -> StreamingResponse:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if CONFIG_PATH.exists():
            archive.writestr("config.json", CONFIG_PATH.read_text())
        if LOG_DIR.exists():
            for log_file in LOG_DIR.glob("*.log"):
                archive.write(log_file, arcname=f"logs/{log_file.name}")
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=croc-bot-export.zip"},
    )


@app.websocket("/ws/state")
async def websocket_state(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(1)
            payload: dict[str, Any]
            if config_result and config_result.errors:
                payload = {"errors": [asdict(err) for err in config_result.errors]}
            else:
                payload = {"state": state.snapshot()}
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        return


if (STATIC_ROOT / "static").exists():
    app.mount("/static", StaticFiles(directory=STATIC_ROOT / "static"), name="static")
