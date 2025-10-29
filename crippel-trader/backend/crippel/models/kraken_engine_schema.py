"""Pydantic v2 schema for Kraken-integrated trading engine."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TradeStat(BaseModel):
    """Aggregated statistics with Kraken fee accounting."""

    model_config = ConfigDict(extra="forbid")

    total_trades: int = Field(default=0, ge=0)
    winning_trades: int = Field(default=0, ge=0)
    losing_trades: int = Field(default=0, ge=0)
    fees_paid: float = Field(default=0.0, ge=0.0)
    realized_pnl: float = Field(default=0.0, ge=0.0)

    def apply_fee(self, amount: float, is_maker: bool) -> float:
        """Apply Kraken maker/taker fee schedule to a trade value."""

        fee_rate = 0.0016 if is_maker else 0.0026
        fee = amount * fee_rate
        self.fees_paid += fee
        return fee

    def record_trade(self, realized_pnl: float, is_winning: bool) -> None:
        """Record the trade outcome and keep win/loss counts aligned."""

        self.total_trades += 1
        if is_winning:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        updated_pnl = self.realized_pnl + realized_pnl
        self.realized_pnl = updated_pnl if updated_pnl >= 0 else 0.0

    @property
    def win_rate(self) -> float:
        return (self.winning_trades / self.total_trades) if self.total_trades else 0.0

    @model_validator(mode="after")
    def _validate_counts(self) -> "TradeStat":
        if self.winning_trades + self.losing_trades > self.total_trades:
            raise ValueError("Winning + losing trades cannot exceed total trades.")
        return self


class RiskConfig(BaseModel):
    """Risk configuration for capital deployment."""

    model_config = ConfigDict(extra="forbid")

    max_pct_per_position: float = Field(default=0.20, ge=0.0, le=1.0)
    max_total_deployed: float = Field(default=0.80, ge=0.0, le=1.0)
    cash_reserve: float = Field(default=0.10, ge=0.0, le=1.0)
    daily_loss_limit: float = Field(default=0.05, ge=0.0, le=1.0)
    max_drawdown: float = Field(default=0.15, ge=0.0, le=1.0)


class TradeExecution(BaseModel):
    """Execution payload for a filled trade."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    side: Literal["buy", "sell"]
    quantity: float = Field(..., ge=0.0)
    price: float = Field(..., ge=0.0)
    is_maker: bool


class EngineState(BaseModel):
    """Stateful metrics for the real-money engine."""

    model_config = ConfigDict(extra="forbid")

    capital: float = Field(default=1000.0, ge=0.0)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    stats: TradeStat = Field(default_factory=TradeStat)

    def execute_trade(self, trade: TradeExecution) -> dict[str, float]:
        """Apply a trade to the engine state using mocked PnL logic."""

        trade_value = trade.price * trade.quantity
        fee = self.stats.apply_fee(trade_value, trade.is_maker)

        # Simple placeholder for realized PnL dynamics
        pnl = trade_value * (0.01 if trade.side == "sell" else -0.01)
        is_winning = pnl >= 0
        realized_component = pnl if is_winning else 0.0
        self.stats.record_trade(realized_pnl=realized_component, is_winning=is_winning)

        self.capital = max(self.capital + pnl - fee, 0.0)
        return {
            "trade_value": trade_value,
            "fee_charged": fee,
            "pnl": pnl,
            "capital": self.capital,
            "total_trades": self.stats.total_trades,
            "winning_trades": self.stats.winning_trades,
            "losing_trades": self.stats.losing_trades,
            "fees_paid": self.stats.fees_paid,
            "realized_pnl": self.stats.realized_pnl,
        }


if __name__ == "__main__":
    state = EngineState()
    sample_trade = TradeExecution(
        symbol="BTC/USD",
        side="sell",
        quantity=0.25,
        price=42000.0,
        is_maker=False,
    )
    result = state.execute_trade(sample_trade)
    print("Executed trade summary:")
    for key, value in result.items():
        print(f"  {key}: {value}")
