"""Integration tests for the FastAPI trading backend."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from pybackend.server import app, market_data_service, trading_mode_service


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def ensure_paper_state():
    trading_mode_service.set_mode("paper")
    market_data_service.tick()


def test_get_assets(client):
    ensure_paper_state()
    response = client.get("/api/assets")
    assert response.status_code == 200
    payload = response.json()
    assert "assets" in payload
    assert isinstance(payload["assets"], list)
    assert len(payload["assets"]) > 0


def test_get_history(client):
    ensure_paper_state()
    symbol = market_data_service.assets[0]["symbol"]
    response = client.get(f"/api/history/{symbol}")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == symbol
    assert isinstance(body["candles"], list)
    assert len(body["candles"]) > 0


def test_post_orders_updates_portfolio(client):
    ensure_paper_state()
    symbol = market_data_service.assets[0]["symbol"]
    order_response = client.post("/api/orders", json={"symbol": symbol, "quantity": 1})
    assert order_response.status_code == 201
    trade = order_response.json()
    assert trade["symbol"] == symbol

    portfolio_response = client.get("/api/portfolio")
    assert portfolio_response.status_code == 200
    portfolio = portfolio_response.json()
    positions = portfolio.get("positions", [])
    assert any(position["symbol"] == symbol and position["quantity"] > 0 for position in positions)
