"""HTTP API endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from .models.enums import Mode
from .models.wire import (
    AssetInfo,
    HistoryPoint,
    ModeChangeRequest,
    SettingsResponse,
    StatsResponse,
    StreamMessage,
)
from .runtime import EngineRuntime

router = APIRouter(prefix="/api")


def get_runtime(request: Request) -> EngineRuntime:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise RuntimeError("runtime not initialized")
    return runtime


@router.get("/assets", response_model=list[AssetInfo])
async def list_assets() -> list[AssetInfo]:
    return [
        AssetInfo(symbol="XBT/USD", description="Bitcoin vs USD", active=True),
        AssetInfo(symbol="ETH/USD", description="Ethereum vs USD", active=False),
    ]


@router.get("/history/{symbol}", response_model=list[HistoryPoint])
async def history(symbol: str, runtime: EngineRuntime = Depends(get_runtime)) -> list[HistoryPoint]:
    ticks = runtime.history(symbol)
    return [HistoryPoint(ts=tick.ts, price=tick.price, volume=tick.volume) for tick in ticks]


@router.get("/orders", response_model=list[StreamMessage])
async def list_orders() -> list[StreamMessage]:
    """Reserved endpoint for future live order history."""
    return []


@router.get("/settings", response_model=SettingsResponse)
async def settings(runtime: EngineRuntime = Depends(get_runtime)) -> SettingsResponse:
    state = runtime.state_service.state
    return SettingsResponse(
        aggression=state.aggression.aggression,
        params=state.aggression,
        mode=state.mode_state.mode,
    )


@router.post("/mode", response_model=SettingsResponse)
async def change_mode(
    payload: ModeChangeRequest,
    runtime: EngineRuntime = Depends(get_runtime),
) -> SettingsResponse:
    if payload.mode == Mode.LIVE and not payload.confirm:
        raise HTTPException(status_code=400, detail="Live mode requires confirmation")
    await runtime.state_service.set_mode(payload.mode, confirmed=payload.confirm)
    state = runtime.state_service.state
    await runtime.connection_manager.broadcast(
        {
            "channel": "mode:update",
            "payload": {"mode": state.mode_state.mode.value, "live": state.mode_state.mode == Mode.LIVE},
            "ts": datetime.utcnow().isoformat(),
        }
    )
    return SettingsResponse(aggression=state.aggression.aggression, params=state.aggression, mode=state.mode_state.mode)


@router.post("/settings/aggression", response_model=SettingsResponse)
async def set_aggression(aggression: int, runtime: EngineRuntime = Depends(get_runtime)) -> SettingsResponse:
    params = await runtime.state_service.set_aggression(aggression)
    runtime.strategy_engine.set_aggression(aggression)
    await runtime.repository.record_aggression(aggression)
    state = runtime.state_service.state
    return SettingsResponse(aggression=params.aggression, params=params, mode=state.mode_state.mode)


@router.get("/stats", response_model=StatsResponse)
async def stats(runtime: EngineRuntime = Depends(get_runtime)) -> StatsResponse:
    snapshot = runtime.portfolio.snapshot(datetime.utcnow())
    stats = runtime.state_service.state.stats
    return StatsResponse(
        pnl=stats.realized_pnl + snapshot.pnl_unrealized,
        win_rate=stats.win_rate,
        fees=stats.fees_paid,
        total_trades=stats.total_trades,
        equity=snapshot.total_equity,
        cash=snapshot.cash,
    )
