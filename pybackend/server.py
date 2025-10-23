"""FastAPI application powering the Crippel Trader control panel."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "dist"
SETTINGS_FILE = BASE_DIR / "settings.json"

BotStatus = Literal["running", "paused", "stopped"]
TradeFrequency = Literal["low", "medium", "high"]


class SettingsPayload(BaseModel):
    """Schema describing the tunable bot settings exposed to the UI."""

    risk: float = Field(..., ge=0.0, le=1.0, description="Risk tolerance between 0 and 1")
    trade_frequency: TradeFrequency
    max_positions: int = Field(..., ge=1, le=100, description="Maximum simultaneous open positions")


class StatusPayload(BaseModel):
    """Schema used to update the bot lifecycle state."""

    status: BotStatus


class SettingsStore:
    """Simple in-memory settings manager with optional JSON persistence."""

    def __init__(self, *, path: Optional[Path] = None) -> None:
        self._path = path
        self._settings = SettingsPayload(risk=0.2, trade_frequency="medium", max_positions=5)
        self._updated_at = datetime.utcnow()
        self._status: BotStatus = "stopped"
        self._status_updated_at = datetime.utcnow()
        self._load_from_disk()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load_from_disk(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text())
            self._settings = SettingsPayload(**payload)
            self._updated_at = datetime.utcnow()
        except Exception:  # pragma: no cover - defensive logging
            # If we cannot load settings we fall back to defaults and keep
            # operating purely in memory. Errors are intentionally swallowed so
            # the application can continue to boot.
            self._settings = SettingsPayload(risk=0.2, trade_frequency="medium", max_positions=5)

    def _write_to_disk(self) -> None:
        if not self._path:
            return
        payload = self._settings.model_dump()
        self._path.write_text(json.dumps(payload, indent=2))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_settings(self) -> Dict[str, Any]:
        data = self._settings.model_dump()
        data["updated_at"] = self._updated_at.isoformat()
        return data

    def update_settings(self, payload: SettingsPayload) -> Dict[str, Any]:
        self._settings = payload
        self._updated_at = datetime.utcnow()
        self._write_to_disk()
        return self.get_settings()

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self._status,
            "updated_at": self._status_updated_at.isoformat(),
        }

    def set_status(self, status: BotStatus) -> Dict[str, Any]:
        self._status = status
        self._status_updated_at = datetime.utcnow()
        return self.get_status()


settings_store = SettingsStore(path=SETTINGS_FILE)

api_router = APIRouter(prefix="/api", tags=["control"])


@api_router.get("/settings")
def read_settings() -> Dict[str, Any]:
    """Return the currently active bot settings."""

    return settings_store.get_settings()


@api_router.post("/settings")
def update_settings(payload: SettingsPayload) -> Dict[str, Any]:
    """Persist new settings and return the updated snapshot."""

    return settings_store.update_settings(payload)


@api_router.get("/status")
def read_status() -> Dict[str, Any]:
    """Expose the lifecycle status of the trading bot."""

    return settings_store.get_status()


@api_router.post("/status")
def update_status(request: StatusPayload) -> Dict[str, Any]:
    """Update the lifecycle status of the trading bot."""

    return settings_store.set_status(request.status)


app = FastAPI(title="Crippel Trader Control Server", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)

static_files: Optional[StaticFiles]
if DIST_DIR.exists():
    static_files = StaticFiles(directory=DIST_DIR, html=True)
    app.mount("/", static_files, name="frontend")
else:  # pragma: no cover - frontend assets may be absent in CI
    static_files = None


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str) -> FileResponse:
    """Return index.html for any unmatched path to support client routing."""

    index_path = DIST_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend has not been built")
    return FileResponse(index_path)


__all__ = ["app", "settings_store", "SettingsPayload"]
