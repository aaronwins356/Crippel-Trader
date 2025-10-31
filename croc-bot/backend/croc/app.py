"""FastAPI application exposing trading controls and telemetry."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .ai_engineer import AIEngineerService, PatchApplicationError
from .ai_engineer.vcs import VCSOperationError
from .bus import EventBus
from .config import RiskLimits, Settings, TradingMode, load_settings
from .data.feed_ccxt import CCXTFeed
from .data.feed_replay import ReplayFeed
from .exec.broker_ccxt import CCXTBroker
from .exec.broker_paper import PaperBroker
from .risk.risk_manager import RiskManager
from .runtime.engine import Engine
from .runtime.metrics import MetricsCollector
from .runtime.scheduler import Scheduler
from .storage.datastore import DataStore
from .storage.model_registry import ModelRegistry
from .strategy.ml_policy import MLPolicyStrategy
from .strategy.rule_sma import SMAStrategy
from .strategy.base import BaseStrategy
from .data.features import FeaturePipeline
from .logging_cfg import configure_logging


class AppContext:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        configure_logging(settings.log_level, settings.storage.base_dir)
        self.bus = EventBus()
        self.metrics = MetricsCollector()
        self.datastore = DataStore(settings.storage)
        self.registry = ModelRegistry(Path(settings.storage.base_dir) / "models")
        self.scheduler = Scheduler()
        self.feature_pipeline = FeaturePipeline(
            fast_window=int(settings.strategy.params.get("fast_window", 12)),
            slow_window=int(settings.strategy.params.get("slow_window", 26)),
            vol_window=int(settings.strategy.params.get("vol_window", 20)),
        )
        self.feed = self._build_feed()
        self.broker = self._build_broker()
        self.risk = RiskManager(settings.risk)
        self.strategy = self._build_strategy()
        self.engine = Engine(
            settings,
            feed=self.feed,
            strategy=self.strategy,
            broker=self.broker,
            risk=self.risk,
            datastore=self.datastore,
            metrics=self.metrics,
            bus=self.bus,
            feature_pipeline=self.feature_pipeline,
            model_registry=self.registry,
        )
        self.scheduler.add_job(30.0, self._emit_metrics)
        repo_root = Path(__file__).resolve().parents[3]
        log_path = Path(settings.storage.base_dir) / "croc.log"
        self.ai = AIEngineerService(
            repo_root=repo_root,
            log_path=log_path,
            metrics_fetcher=self.metrics.rollup,
            bus=self.bus,
        )

    def _build_feed(self):
        feed_cfg = self.settings.feed
        if feed_cfg.source == "ccxt":
            if self.settings.mode is not TradingMode.LIVE:
                raise RuntimeError("CCXT feed requires live mode")
            credentials = {
                "apiKey": self.settings.api_key,
                "secret": self.settings.api_secret,
                "password": self.settings.api_passphrase,
            }
            return CCXTFeed(
                exchange=self.settings.exchange or "binance",
                symbol=feed_cfg.symbol,
                timeframe=feed_cfg.timeframe,
                credentials={k: v for k, v in credentials.items() if v},
            )
        path = feed_cfg.replay_path if feed_cfg.replay_path else None
        return ReplayFeed(feed_cfg.symbol, path)

    def _build_broker(self):
        if self.settings.execution.broker == "paper" or self.settings.mode == TradingMode.PAPER:
            return PaperBroker(
                slippage_bps=self.settings.execution.slippage_bps,
                fee_bps=self.settings.execution.fee_bps,
            )
        if self.settings.mode is not TradingMode.LIVE:
            raise RuntimeError("Live broker requires live mode")
        credentials = {
            "apiKey": self.settings.api_key,
            "secret": self.settings.api_secret,
            "password": self.settings.api_passphrase,
        }
        return CCXTBroker(self.settings.exchange or "binance", credentials=credentials)

    def _build_strategy(self) -> BaseStrategy:
        name = self.settings.strategy.name
        if name == "rule_sma":
            return SMAStrategy(self.settings.strategy)
        if name == "ml_policy":
            return MLPolicyStrategy(self.settings.strategy, self.registry)
        raise ValueError(f"Unknown strategy: {name}")

    async def _emit_metrics(self) -> None:
        snapshot = await self.engine.metrics_snapshot()
        await self.bus.publish("metrics", snapshot.model_dump())


def get_context(app: FastAPI) -> AppContext:
    ctx: AppContext = app.state.ctx
    return ctx


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    ctx = AppContext(settings)
    app.state.ctx = ctx
    if settings.mode is TradingMode.PAPER:
        await ctx.engine.start()
    await ctx.scheduler.start()
    try:
        yield
    finally:
        await ctx.engine.stop()
        await ctx.scheduler.stop()
        await ctx.bus.close()


def create_app() -> FastAPI:
    app = FastAPI(title="croc-bot", default_response_class=ORJSONResponse, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def health(ctx: AppContext = Depends(lambda: get_context(app))):
        return {
            "status": "ok",
            "engine_running": ctx.engine.running,
            "mode": ctx.settings.mode.value,
        }

    @app.get("/version")
    async def version():
        return {"version": __version__}

    @app.get("/metrics")
    async def metrics(ctx: AppContext = Depends(lambda: get_context(app))):
        snapshot = await ctx.engine.metrics_snapshot()
        return snapshot.model_dump()

    @app.get("/config")
    async def config(ctx: AppContext = Depends(lambda: get_context(app))):
        return ctx.settings.model_dump(mode="json")

    @app.post("/controls/start")
    async def start_engine(ctx: AppContext = Depends(lambda: get_context(app))):
        await ctx.engine.start()
        return {"engine_running": True}

    @app.post("/controls/stop")
    async def stop_engine(ctx: AppContext = Depends(lambda: get_context(app))):
        await ctx.engine.stop()
        return {"engine_running": False}

    @app.post("/controls/model")
    async def set_model(payload: dict[str, Any], ctx: AppContext = Depends(lambda: get_context(app))):
        model_path = payload.get("path")
        if not model_path:
            raise HTTPException(status_code=400, detail="path required")
        artifact = Path(model_path)
        if not artifact.exists():
            raise HTTPException(status_code=404, detail="model not found")
        ctx.registry.set_active(artifact)
        return {"active_model": str(artifact)}

    @app.post("/controls/kill-switch")
    async def kill_switch(payload: dict[str, Any], ctx: AppContext = Depends(lambda: get_context(app))):
        active = bool(payload.get("active", True))
        if active:
            ctx.risk.activate_kill_switch()
        else:
            ctx.risk.deactivate_kill_switch()
        return {"kill_switch": ctx.risk.state.kill_switch}

    @app.post("/controls/risk")
    async def update_risk(payload: dict[str, Any], ctx: AppContext = Depends(lambda: get_context(app))):
        try:
            limits = RiskLimits.model_validate({**ctx.settings.risk.model_dump(mode="json"), **payload})
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))
        ctx.settings.risk = limits
        ctx.risk.limits = limits
        return limits.model_dump(mode="json")

    class AISuggestRequest(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        issue: str
        context_files: list[str] = Field(default_factory=list, alias="contextFiles")

    class AIApplyRequest(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        diff: str
        allow_add_dep: bool = Field(default=False)

    @app.post("/ai/suggest")
    async def ai_suggest(payload: AISuggestRequest, ctx: AppContext = Depends(lambda: get_context(app))):
        suggestion = await ctx.ai.suggest(payload.issue, payload.context_files)
        return suggestion.model_dump()

    @app.post("/ai/apply")
    async def ai_apply(payload: AIApplyRequest, ctx: AppContext = Depends(lambda: get_context(app))):
        try:
            report = await ctx.ai.apply(payload.diff, payload.allow_add_dep)
        except PatchApplicationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except VCSOperationError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return report.model_dump()

    @app.post("/ai/rollback")
    async def ai_rollback(ctx: AppContext = Depends(lambda: get_context(app))):
        try:
            branch = await ctx.ai.rollback()
        except VCSOperationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"branch": branch}

    @app.get("/ai/status")
    async def ai_status(ctx: AppContext = Depends(lambda: get_context(app))):
        return await ctx.ai.status()

    @app.websocket("/ws/stream")
    async def stream(websocket: WebSocket):
        await websocket.accept()
        topic = websocket.query_params.get("topic", "ticks")
        ctx = get_context(app)
        async with ctx.bus.subscribe(topic) as queue:
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    await websocket.send_json({"topic": topic, "data": item})
            except WebSocketDisconnect:
                return

    @app.websocket("/ws/ai")
    async def ai_events(websocket: WebSocket):
        await websocket.accept()
        ctx = get_context(app)
        async with ctx.bus.subscribe("ai") as queue:
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    await websocket.send_json(item)
            except WebSocketDisconnect:
                return

    return app


app = create_app()
