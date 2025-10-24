"""HTTP routes for the Crippel-Firm backend."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from pydantic import BaseModel

from .settings import AppSettings, get_settings
from .firm.manager import ManagerBot

router = APIRouter(prefix="/firm")


def get_manager(scope: Request | WebSocket) -> ManagerBot:
    manager: ManagerBot | None = getattr(scope.app.state, "manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="Manager not initialized")
    return manager


class HireRequest(BaseModel):
    role: str


class ModeChange(BaseModel):
    mode: str
    confirm: bool = False


class AggressionUpdate(BaseModel):
    aggression: int


@router.get("/status")
async def status(manager: ManagerBot = Depends(get_manager)) -> dict[str, Any]:
    return manager.status()


@router.post("/hire")
async def hire(payload: HireRequest, manager: ManagerBot = Depends(get_manager)) -> dict[str, str]:
    bot_id = await manager.hire(payload.role)
    return {"bot_id": bot_id}


@router.post("/fire/{bot_id}")
async def fire(bot_id: str, manager: ManagerBot = Depends(get_manager)) -> dict[str, str]:
    await manager.fire(bot_id, reason="api")
    return {"status": "terminated"}


@router.get("/bots")
async def bots(manager: ManagerBot = Depends(get_manager)) -> list[dict[str, Any]]:
    return manager.status()["workers"]


@router.get("/settings")
async def read_settings(settings: AppSettings = Depends(get_settings)) -> dict[str, Any]:
    return settings.model_dump()


@router.post("/mode")
async def set_mode(
    payload: ModeChange,
    settings: AppSettings = Depends(get_settings),
    manager: ManagerBot = Depends(get_manager),
) -> dict[str, Any]:
    if payload.mode == "live" and not payload.confirm:
        raise HTTPException(status_code=400, detail="Live mode requires confirmation")
    settings.mode.mode = payload.mode
    manager.mode = payload.mode
    return {"mode": payload.mode}


@router.post("/settings/aggression")
async def set_aggression(payload: AggressionUpdate, settings: AppSettings = Depends(get_settings)) -> dict[str, Any]:
    settings.aggression.default = max(1, min(payload.aggression, 10))
    return {"aggression": settings.aggression.default}
