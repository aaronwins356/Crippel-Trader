from __future__ import annotations

from fastapi.testclient import TestClient

from crippel.app import create_app


def test_settings_endpoint() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    assert "aggression" in payload
    assert payload["mode"] == "paper"


def test_assets_endpoint() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/assets")
    assert response.status_code == 200
    assets = response.json()
    assert any(asset["symbol"] == "XBT/USD" for asset in assets)
