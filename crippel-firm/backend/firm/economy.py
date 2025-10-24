"""Firm-level economy and scoring."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

import orjson

from .config import CapitalPolicy
from .engine.portfolio import Portfolio
from .utils.metrics import PerformanceLedger, calculate_drawdown


@dataclass
class FirmState:
    equity_curve: list[float] = field(default_factory=list)
    conscience_score: float = 0.0
    last_updated: float = field(default_factory=time.time)


class FirmEconomy:
    """Tracks firm-level performance and persistence."""

    def __init__(self, capital_policy: CapitalPolicy, state_path: Path) -> None:
        self.capital_policy = capital_policy
        self.state_path = state_path
        self.portfolio = Portfolio(cash=capital_policy.starting_equity)
        self.ledger = PerformanceLedger()
        self.state = FirmState(equity_curve=[capital_policy.starting_equity])

    def update_equity(self, equity: float) -> None:
        self.state.equity_curve.append(equity)
        drawdown = calculate_drawdown(self.state.equity_curve)
        profitability = (equity - self.capital_policy.starting_equity) / self.capital_policy.starting_equity
        risk_penalty = drawdown + max(0.0, self.portfolio.current_exposure() - self.capital_policy.max_position_usd) / self.capital_policy.max_position_usd
        self.state.conscience_score = profitability - risk_penalty
        self.state.last_updated = time.time()

    def serialize(self) -> None:
        payload = {
            "equity_curve": self.state.equity_curve,
            "conscience_score": self.state.conscience_score,
            "last_updated": self.state.last_updated,
        }
        self.state_path.write_bytes(orjson.dumps(payload))

    def load(self) -> None:
        if not self.state_path.exists():
            return
        data = orjson.loads(self.state_path.read_bytes())
        self.state = FirmState(
            equity_curve=list(map(float, data.get("equity_curve", []))) or [self.capital_policy.starting_equity],
            conscience_score=float(data.get("conscience_score", 0.0)),
            last_updated=float(data.get("last_updated", time.time())),
        )

    def performance_summary(self) -> Dict[str, float]:
        equity = self.state.equity_curve[-1]
        drawdown = calculate_drawdown(self.state.equity_curve)
        return {
            "equity": equity,
            "drawdown": drawdown,
            "conscience_score": self.state.conscience_score,
        }
