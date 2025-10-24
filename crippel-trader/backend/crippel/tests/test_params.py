from __future__ import annotations

import pytest

from crippel.engine.params import tune_params


def test_tune_params_bounds() -> None:
    params = tune_params(5)
    assert 0 < params.position_fraction <= 0.5
    assert params.stop_distance > 0
    assert params.take_profit_distance > params.stop_distance
    assert params.signal_threshold >= 0


@pytest.mark.parametrize("level", [1, 10])
def test_tune_params_range(level: int) -> None:
    params = tune_params(level)
    assert params.aggression == level
