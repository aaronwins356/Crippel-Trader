# Modular ML/RL Architecture Blueprint

This document outlines the proposed modular architecture for Croc-Bot to support
high-performance trading workflows with ML and RL integration.

## Directory Layout

```
data/           # Data ingestion, normalization, and feature engineering
models/         # ML/RL abstractions, factories, and adapters
strategies/     # Strategy implementations orchestrating models and signals
executors/      # Order execution clients and backpressure-aware workflows
pipelines/      # Offline/online training, evaluation, and backtesting flows
orchestration/  # Application runtime loops and service orchestration
utils/          # Shared utilities (config, logging, metrics, DI)
```

Existing `core/` modules remain intact during the migration window. New
functionality should be implemented inside the modular packages above. Once the
new components reach feature parity, legacy modules can be deprecated and
removed.

## Design Principles

1. **Separation of Concerns** – isolate data handling, modeling, strategies,
   execution, and orchestration into well-defined modules.
2. **Async-first Execution** – prefer non-blocking coroutines for IO and
   CPU-bound workloads wrapped with executors.
3. **Typed Interfaces** – rely on `typing.Protocol` and dataclasses to establish
   stable contracts across modules.
4. **Dependency Injection** – use `utils.service_container.ServiceContainer` to
   construct and share dependencies explicitly.
5. **Observability** – adopt `structlog` for JSON logs and Prometheus metrics for
   operational visibility.
6. **Config-driven Behavior** – define strongly validated Pydantic models under
   `utils.config` to manage runtime configuration.

## Migration Checklist

- [ ] Migrate existing data feeders to implement `MarketDataSource`/
      `MarketDataStream` protocols.
- [ ] Port feature engineering logic into `data.preprocessing` and integrate
      vectorized computations.
- [ ] Wrap current ML components using `models.base.ModelBundle` and
      `models.rl.RLModelBundle`.
- [ ] Refactor strategies to subclass `strategies.base.ModelDrivenStrategy` and
      register them via `StrategyFactory` for runtime selection.
- [ ] Replace synchronous order handlers with `executors.async_executor` to
      ensure deterministic concurrency limits and backpressure control.
- [ ] Instrument key code paths with structured logs and Prometheus metrics.
- [ ] Implement integration tests covering async pipelines and failure modes.

## Sample Wiring

```python
from data.ingestion import InMemoryStream, RollingFeatureStore
from models.base import InferenceAdapter
from strategies.base import StrategyFactory
from executors.async_executor import MarketOrderExecutor
from orchestration.live_trading import run_live_loop
from utils.config import AppConfig
from utils.logging import configure_logging
from utils.service_container import ServiceContainer

config = AppConfig.from_dict({...})
configure_logging()

container = ServiceContainer()
container.register("feature_store", lambda _: RollingFeatureStore(window=256))
container.register("strategy", lambda c: StrategyFactory().create(
    config.strategy.model_dump(),
    model=InferenceAdapter(model=...),
))
container.register("executor", lambda c: MarketOrderExecutor(client=...))

strategy = container.resolve("strategy")
executor = container.resolve("executor")

asyncio.run(run_live_loop(
    data_stream=InMemoryStream(queue),
    strategy=strategy,
    submit_order=lambda frame: executor.on_signal(...),
))
```

This blueprint provides the scaffolding for incremental adoption without
breaking current behavior.

## AI Code Refactor Agent

An optional `ai_agent` package embeds an autonomous developer workflow inside
the bot. The `AICodeRefactorAgent` class coordinates a closed loop that:

1. **Monitors** structured JSON logs and metrics snapshots for anomalies such as
   repeated exceptions or latency spikes.
2. **Analyzes** affected code using an LLM client implementation and a
   `CodebaseInspector` that extracts the relevant source context.
3. **Proposes** fixes as unified diffs via the LLM integration. Patches include
   human-readable rationales and a confidence score.
4. **Validates** proposed changes inside an isolated workspace by compiling
   modified modules and executing configurable test commands (default: `pytest`).
5. **Applies** approved diffs to the repository when `apply_changes=True` in the
   agent configuration.

All intermediate decisions, including rejected patches, are logged for human
review. The agent persists issue fingerprints in memory during a session to
avoid redundant analysis and integrates with the monitoring stack by reading the
same log and metrics outputs produced by the runtime engine.
