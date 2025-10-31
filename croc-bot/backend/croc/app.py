"""FastAPI application exposing trading controls and telemetry."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
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
from .data.feed_simulated import SimulatedFeed
from .exec.broker_ccxt import CCXTBroker
from .exec.broker_paper import PaperBroker
from .risk.risk_manager import RiskManager
from .runtime.engine import Engine
from .runtime.metrics import MetricsCollector
from .runtime.scheduler import Scheduler
from .runtime.simulation import AISimulationController
from .storage.datastore import DataStore
from .storage.model_registry import ModelRegistry
from .rl.schedule import LearningSchedule
from .rl.promote import Promoter
from .rl.train import TrainConfig
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
        self.scheduler = Scheduler(self.bus)
        self._lifecycle_lock = asyncio.Lock()
        self._started = False
        self.feature_pipeline = FeaturePipeline(
            fast_window=int(settings.strategy.params.get("fast_window", 12)),
            slow_window=int(settings.strategy.params.get("slow_window", 26)),
            vol_window=int(settings.strategy.params.get("vol_window", 20)),
        )
        self.feed = self._build_feed()
        self.broker = self._build_broker()
        self.risk = RiskManager(settings.risk, bus=self.bus)
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
        self.promoter = Promoter(self.registry, bus=self.bus)
        self.learning = LearningSchedule(
            settings,
            registry=self.registry,
            promoter=self.promoter,
            bus=self.bus,
            risk=self.risk,
        )
        self.scheduler.add_job(timedelta(seconds=30), self._emit_metrics, name="metrics.emit")
        self.scheduler.add_job(timedelta(hours=24), self.learning.run_training, name="rl.train")
        self.scheduler.add_job(
            timedelta(days=7),
            lambda: self.learning.run_evaluation(shadow=True),
            name="rl.evaluate",
        )
        repo_root = Path(__file__).resolve().parents[3]
        log_path = Path(settings.storage.base_dir) / "croc.log"
        self.ai = AIEngineerService(
            repo_root=repo_root,
            log_path=log_path,
            metrics_fetcher=self.metrics.rollup,
            bus=self.bus,
        )
        self.simulation: AISimulationController | None = None
        if self.settings.mode is TradingMode.AI_SIMULATION:
            self.simulation = AISimulationController(
                settings=self.settings,
                metrics=self.metrics,
                strategy=self.strategy,
                bus=self.bus,
            )
            interval = timedelta(seconds=self.settings.simulation.reconfigure_interval_seconds)
            self.scheduler.add_job(interval, self.simulation.reconfigure, name="simulation.reconfigure")

    def _build_feed(self):
        feed_cfg = self.settings.feed
        if self.settings.mode is TradingMode.AI_SIMULATION or feed_cfg.source == "simulation":
            sim_cfg = self.settings.simulation
            return SimulatedFeed(
                feed_cfg.symbol,
                base_price=sim_cfg.base_price,
                volatility=sim_cfg.volatility,
                interval_seconds=sim_cfg.interval_seconds,
                seed=sim_cfg.seed,
            )
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
        if (
            self.settings.mode in {TradingMode.PAPER, TradingMode.AI_SIMULATION}
            or self.settings.execution.broker == "paper"
        ):
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

    async def startup(self) -> None:
        async with self._lifecycle_lock:
            if self._started:
                return
            if self.settings.mode in {TradingMode.PAPER, TradingMode.AI_SIMULATION}:
                await self.engine.start()
            await self.scheduler.start()
            self._started = True

    async def shutdown(self) -> None:
        async with self._lifecycle_lock:
            if not self._started:
                return
            await self.engine.stop()
            await self.scheduler.stop()
            await self.bus.close()
            self._started = False


def get_context(app: FastAPI) -> AppContext:
    ctx: AppContext = app.state.ctx
    return ctx


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    ctx = AppContext(settings)
    app.state.ctx = ctx
    await ctx.startup()
    try:
        yield
    finally:
        await ctx.shutdown()


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

    class TrainRequest(BaseModel):
        algo: str = "ppo"
        seed: int = 42
        epochs: int = 10
        lr: float = Field(default=3e-4, alias="learning_rate")
        train_since: datetime | None = None
        train_until: datetime | None = None

    class EvaluateRequest(BaseModel):
        version: str | None = None
        shadow: bool = False

    class PromoteRequest(BaseModel):
        version: str
        metrics: dict[str, float]

    class RollbackRequest(BaseModel):
        version: str | None = None

    class ModeRequest(BaseModel):
        mode: str

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

    @app.post("/rl/train")
    async def rl_train(payload: TrainRequest, ctx: AppContext = Depends(lambda: get_context(app))):
        config = TrainConfig(
            algo=payload.algo,
            seed=payload.seed,
            epochs=payload.epochs,
            learning_rate=payload.lr,
            train_since=payload.train_since,
            train_until=payload.train_until,
        )
        result = await ctx.learning.run_training(config)
        return {
            "version": result.version,
            "metadata": result.metadata,
        }

    @app.post("/rl/evaluate")
    async def rl_evaluate(payload: EvaluateRequest, ctx: AppContext = Depends(lambda: get_context(app))):
        result = await ctx.learning.run_evaluation(version=payload.version, shadow=payload.shadow)
        response: dict[str, object] = {"metrics": result.metrics}
        if result.compare_path:
            response["compare_path"] = str(result.compare_path)
        if result.log_path:
            response["shadow_log"] = str(result.log_path)
        return response

    @app.post("/rl/promote")
    async def rl_promote(payload: PromoteRequest, ctx: AppContext = Depends(lambda: get_context(app))):
        gate = await ctx.learning.run_promotion(payload.version, payload.metrics)
        return {"passed": gate.passed, "reasons": gate.reasons}

    @app.post("/rl/rollback")
    async def rl_rollback(payload: RollbackRequest, ctx: AppContext = Depends(lambda: get_context(app))):
        rolled = await ctx.learning.rollback(payload.version)
        return {"active_version": rolled.version}

    @app.get("/rl/registry")
    async def rl_registry(ctx: AppContext = Depends(lambda: get_context(app))):
        versions = [
            {
                "version": model.version,
                "created_at": model.created_at.isoformat(),
                "code_sha": model.code_sha,
                "metrics": model.metrics,
                "config": model.config,
                "data_span": model.data_span,
                "path": str(model.path),
            }
            for model in ctx.registry.list_versions()
        ]
        active = ctx.registry.active_version()
        return {"active": active.version if active else None, "versions": versions}

    @app.get("/rl/shadow_status")
    async def rl_shadow_status(ctx: AppContext = Depends(lambda: get_context(app))):
        return ctx.learning.get_shadow_status() or {}

    @app.get("/mode")
    async def read_mode(ctx: AppContext = Depends(lambda: get_context(app))):
        return {"mode": ctx.settings.mode.external_name}

    @app.post("/mode")
    async def update_mode(payload: ModeRequest, ctx: AppContext = Depends(lambda: get_context(app))):
        try:
            target = TradingMode.from_external(payload.mode)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if target is ctx.settings.mode:
            return {"mode": ctx.settings.mode.external_name}
        updated = ctx.settings.model_dump(mode="json")
        updated["mode"] = target.value
        new_settings = Settings.model_validate(updated)
        if target is TradingMode.LIVE and new_settings.mode is not TradingMode.LIVE:
            reason = new_settings.simulation_auto_reason or "credentials missing"
            raise HTTPException(status_code=400, detail=f"Live trading unavailable: {reason}")
        new_ctx = AppContext(new_settings)
        try:
            await ctx.shutdown()
            app.state.ctx = new_ctx
            await new_ctx.startup()
        except Exception as exc:  # noqa: BLE001
            app.state.ctx = ctx
            await ctx.startup()
            raise HTTPException(status_code=500, detail=f"Failed to switch mode: {exc}") from exc
        return {"mode": new_ctx.settings.mode.external_name}

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
