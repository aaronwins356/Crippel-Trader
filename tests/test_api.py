"""Integration tests for the FastAPI trading control backend."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from pybackend.server import SettingsPayload, app, settings_store

DEFAULT_SETTINGS = {
    "risk": 0.2,
    "trade_frequency": "medium",
    "max_positions": 5,
}


@pytest.fixture(autouse=True)
def reset_state():
    """Ensure each test runs with a predictable settings baseline."""

    settings_store.update_settings(SettingsPayload(**DEFAULT_SETTINGS))
    settings_store.set_status("stopped")
    yield
    settings_store.update_settings(SettingsPayload(**DEFAULT_SETTINGS))
    settings_store.set_status("stopped")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_get_settings_returns_defaults(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    for key, value in DEFAULT_SETTINGS.items():
        if isinstance(value, float):
            assert payload[key] == pytest.approx(value)
        else:
            assert payload[key] == value
    assert "updated_at" in payload


def test_can_update_settings(client):
    new_payload = {
        "risk": 0.35,
        "trade_frequency": "high",
        "max_positions": 12,
    }
    response = client.post("/api/settings", json=new_payload)
    assert response.status_code == 200
    updated = response.json()
    for key, value in new_payload.items():
        if isinstance(value, float):
            assert updated[key] == pytest.approx(value)
        else:
            assert updated[key] == value

    # Verify persistence via a subsequent GET.
    follow_up = client.get("/api/settings")
    assert follow_up.status_code == 200
    persisted = follow_up.json()
    for key, value in new_payload.items():
        if isinstance(value, float):
            assert persisted[key] == pytest.approx(value)
        else:
            assert persisted[key] == value


def test_rejects_invalid_settings(client):
    response = client.post(
        "/api/settings",
        json={"risk": 2, "trade_frequency": "medium", "max_positions": 5},
    )
    assert response.status_code == 422


def test_status_round_trip(client):
    status_response = client.get("/api/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "stopped"

    update_response = client.post("/api/status", json={"status": "running"})
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "running"

    final_response = client.get("/api/status")
    assert final_response.status_code == 200
    assert final_response.json()["status"] == "running"
