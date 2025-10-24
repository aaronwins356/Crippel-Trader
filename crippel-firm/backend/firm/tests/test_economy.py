from pathlib import Path

from firm.config import FirmConfig
from firm.economy import FirmEconomy


def test_economy_updates_and_persists(tmp_path):
    config = FirmConfig()
    state_path = tmp_path / "state.json"
    economy = FirmEconomy(config.capital, Path(state_path))
    economy.update_equity(110_000)
    summary = economy.performance_summary()
    assert summary["equity"] == economy.state.equity_curve[-1]
    economy.serialize()
    assert state_path.exists()
    loaded = FirmEconomy(config.capital, Path(state_path))
    loaded.load()
    assert loaded.state.equity_curve[-1] == economy.state.equity_curve[-1]
