"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .api import router as api_router
from .logging import configure_logging
from .runtime import EngineRuntime


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Crippel Trader", default_response_class=ORJSONResponse)
    runtime = EngineRuntime()
    manager = runtime.connection_manager

    @app.on_event("startup")
    async def startup() -> None:  # pragma: no cover - executed at runtime
        await runtime.startup(app)

    @app.on_event("shutdown")
    async def shutdown() -> None:  # pragma: no cover - executed at runtime
        await runtime.shutdown()

    @app.websocket("/ws/stream")
    async def websocket_endpoint(websocket):  # type: ignore[no-untyped-def]
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            await manager.disconnect(websocket)

    app.include_router(api_router)
    return app


app = create_app()
