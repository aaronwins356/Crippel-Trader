"""API routes for managing the firm."""
from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from ..economy import FirmEconomy
from ..manager import ManagerBot


def register_routes(app: FastAPI, manager: ManagerBot) -> None:
    router = APIRouter()

    @router.get("/status")
    async def status() -> dict[str, float]:
        return manager.economy.performance_summary()

    @router.get("/bots")
    async def bots() -> list[dict[str, object]]:
        return [
            {
                "bot_id": record.bot.bot_id,
                "bot_type": record.bot_type,
                "score": record.last_score,
            }
            for record in manager.registry.active_bots()
        ]

    @router.post("/hire/{bot_type}")
    async def hire(bot_type: str) -> dict[str, str]:
        bot_type = bot_type.lower()
        if bot_type == "research":
            bot_id = await manager.hire_research_bot()
        elif bot_type == "analyst":
            bot_id = await manager.hire_analyst_bot()
        elif bot_type == "trader":
            bot_id = await manager.hire_trader_bot()
        elif bot_type == "risk":
            bot_id = await manager.hire_risk_bot()
        else:
            raise HTTPException(status_code=400, detail="Unknown bot type")
        return {"bot_id": bot_id}

    @router.delete("/fire/{bot_id}")
    async def fire(bot_id: str) -> dict[str, str]:
        await manager.fire(bot_id)
        return {"bot_id": bot_id}

    app.include_router(router, prefix="/api/firm")
