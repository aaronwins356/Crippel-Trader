"""FastAPI application for the firm."""
from __future__ import annotations

from fastapi import FastAPI

from ..config import FirmConfig
from ..manager import ManagerBot
from .routes import register_routes


def create_app(config: FirmConfig | None = None) -> FastAPI:
    config = config or FirmConfig()
    manager = ManagerBot(config)
    app = FastAPI(title="Crippel-Firm API")
    register_routes(app, manager)
    return app
