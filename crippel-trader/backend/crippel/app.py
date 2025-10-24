"""Enhanced FastAPI application factory for Croc-Bot trading system."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .api import router as api_router
from .config import get_settings
from .logging import configure_logging
from .enhanced_runtime import EnhancedEngineRuntime


def create_app() -> FastAPI:
    """Create the FastAPI application with enhanced trading capabilities."""
    configure_logging()
    settings = get_settings()
    
    app = FastAPI(
        title="Croc-Bot Trading System",
        description="Professional autonomous trading system with AI strategy generation",
        version="1.0.0",
        default_response_class=ORJSONResponse
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize enhanced runtime
    runtime = EnhancedEngineRuntime()
    manager = runtime.connection_manager

    @app.on_event("startup")
    async def startup() -> None:  # pragma: no cover - executed at runtime
        await runtime.startup(app)

    @app.on_event("shutdown")
    async def shutdown() -> None:  # pragma: no cover - executed at runtime
        await runtime.shutdown()

    @app.websocket("/ws/stream")
    async def websocket_endpoint(websocket):  # type: ignore[no-untyped-def]
        """WebSocket endpoint for real-time data streaming."""
        await manager.connect(websocket)
        try:
            while True:
                # Keep connection alive and handle client messages
                message = await websocket.receive_text()
                # Echo back for now - could handle client commands in the future
                await websocket.send_text(f"Received: {message}")
        except Exception:
            await manager.disconnect(websocket)

    # Include API routes
    app.include_router(api_router)
    
    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with system information."""
        return {
            "name": "Croc-Bot Trading System",
            "version": "1.0.0",
            "description": "Professional autonomous trading system",
            "status": "operational",
            "features": [
                "Paper Trading",
                "Real-time Market Data",
                "Multiple Trading Strategies",
                "Risk Management",
                "Discord Notifications",
                "Professional Dashboard"
            ]
        }
    
    return app


# Create the application instance
app = create_app()
