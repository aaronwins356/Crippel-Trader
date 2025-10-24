"""Parameter tuning based on aggression."""
from __future__ import annotations

from dataclasses import dataclass

from ..models.core import AggressionParams
from ..models.enums import OrderType


@dataclass(frozen=True)
class ParamsGradient:
    position_fraction_min: float = 0.05
    position_fraction_max: float = 0.4
    stop_distance_min: float = 0.002
    stop_distance_max: float = 0.01
    take_profit_min: float = 0.003
    take_profit_max: float = 0.02
    hold_min: float = 5.0
    hold_max: float = 60.0
    cooldown_min: float = 2.0
    cooldown_max: float = 30.0
    threshold_min: float = 0.2
    threshold_max: float = 0.6


def _scale(value: float, min_value: float, max_value: float) -> float:
    return min_value + value * (max_value - min_value)


def tune_params(aggression: int) -> AggressionParams:
    """Return deterministic parameters for aggression levels 1-10."""
    if not 1 <= aggression <= 10:
        raise ValueError("aggression must be between 1 and 10 inclusive")
    g = ParamsGradient()
    norm = (aggression - 1) / 9
    position_fraction = _scale(norm, g.position_fraction_min, g.position_fraction_max)
    stop_distance = _scale(1 - norm, g.stop_distance_min, g.stop_distance_max)
    take_profit_distance = _scale(norm, g.take_profit_min, g.take_profit_max)
    min_hold = _scale(1 - norm, g.hold_min, g.hold_max)
    cooldown = _scale(norm, g.cooldown_min, g.cooldown_max)
    threshold = _scale(1 - norm, g.threshold_min, g.threshold_max)
    maker_bias = 1 - norm * 0.7
    order_type = OrderType.MARKET if norm > 0.5 else OrderType.LIMIT
    return AggressionParams(
        aggression=aggression,
        position_fraction=position_fraction,
        order_type=order_type,
        stop_distance=stop_distance,
        take_profit_distance=take_profit_distance,
        min_hold_time_s=min_hold,
        cooldown_s=cooldown,
        signal_threshold=threshold,
        maker_bias=maker_bias,
    )
