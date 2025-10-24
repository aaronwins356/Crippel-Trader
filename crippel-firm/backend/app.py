"""FastAPI application wiring the firm manager."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .firm.brain import ManagerBrain
from .logging import configure_logging
from .routes import router
from .settings import AppSettings, get_settings
from .ws import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings: AppSettings = get_settings()
    brain = ManagerBrain(settings)
    app.state.settings = settings
    app.state.manager = brain.manager
    app.state.brain = brain
    await brain.start()
    try:
        yield
    finally:
        await brain.stop()


app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)
app.include_router(router)
app.include_router(ws_router)
