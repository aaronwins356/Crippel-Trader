from __future__ import annotations

from pathlib import Path

from croc.config import Settings, TradingMode


def _configure_storage(monkeypatch, base: Path) -> None:
    monkeypatch.setenv("CROC_STORAGE__BASE_DIR", str(base))
    monkeypatch.setenv("CROC_STORAGE__TICKS", str(base / "ticks"))
    monkeypatch.setenv("CROC_STORAGE__TRADES", str(base / "trades"))
    monkeypatch.setenv("CROC_STORAGE__METRICS", str(base / "metrics"))


def test_mode_alias_for_simulation(monkeypatch, tmp_path):
    for key in ["MODE", "CROC_MODE", "CROC_EXCHANGE", "CROC_API_KEY", "CROC_API_SECRET", "CROC_API_PASSPHRASE"]:
        monkeypatch.delenv(key, raising=False)
    _configure_storage(monkeypatch, tmp_path / "storage")
    monkeypatch.setenv("MODE", "AI_SIMULATION")

    settings = Settings.load(None)

    assert settings.mode is TradingMode.AI_SIMULATION
    assert settings.feed.source == "simulation"
    assert settings.execution.broker == "paper"


def test_auto_fallback_without_kraken_keys(monkeypatch, tmp_path):
    for key in ["MODE", "CROC_MODE", "CROC_EXCHANGE", "CROC_API_KEY", "CROC_API_SECRET", "CROC_API_PASSPHRASE"]:
        monkeypatch.delenv(key, raising=False)
    _configure_storage(monkeypatch, tmp_path / "storage")
    monkeypatch.setenv("CROC_MODE", "live")
    monkeypatch.setenv("CROC_EXCHANGE", "kraken")

    settings = Settings.load(None)

    assert settings.mode is TradingMode.AI_SIMULATION
    assert settings.simulation_auto_reason is not None
    assert "Missing Kraken credentials" in settings.simulation_auto_reason
