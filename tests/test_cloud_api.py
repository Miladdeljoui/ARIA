import time

import pytest
from fastapi.testclient import TestClient

from cloud import aria_cloud as api


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(api, "TRIAL_DAYS", 30)
    monkeypatch.setattr(api, "MONTHLY_PRICE_TOMAN", 99000)
    with api.db() as connection:
        connection.execute(
            "INSERT INTO settings(key, value) VALUES('pairing_code', ?)",
            (api.sha256("123456"),),
        )
        connection.commit()
    return TestClient(api.app)


def pair(client):
    response = client.post(
        "/pair", json={"code": "123456", "device_name": "test-phone"}
    )
    assert response.status_code == 200
    return response.json()["token"]


def test_home_and_status_are_available(client, monkeypatch):
    monkeypatch.setattr(api, "hosted_ai_configured", lambda: False)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["assistant"] == "ARIA"
    assert client.get("/status").status_code == 200


def test_pair_rejects_wrong_code(client):
    response = client.post(
        "/pair", json={"code": "000000", "device_name": "test-phone"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_pairing_code"


def test_pair_and_subscription_start_30_day_trial(client):
    token = pair(client)
    response = client.get("/subscription", headers={"X-ARIA-Token": token})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "trial"
    assert body["trial_days"] == 30
    assert body["monthly_price_toman"] == 99000
    assert body["access_granted"] is True


def test_subscription_requires_valid_token(client):
    response = client.get("/subscription", headers={"X-ARIA-Token": "invalid"})
    assert response.status_code == 401


def test_feedback_requires_pairing_and_saves_valid_feedback(client):
    unauthorized = client.post(
        "/feedback", json={"category": "idea", "message": "Add dark mode"}
    )
    assert unauthorized.status_code == 401

    token = pair(client)
    response = client.post(
        "/feedback",
        headers={"X-ARIA-Token": token},
        json={"category": "idea", "message": "Add dark mode", "app_version": "0.3.0"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_feedback_rejects_unknown_category(client):
    token = pair(client)
    response = client.post(
        "/feedback",
        headers={"X-ARIA-Token": token},
        json={"category": "admin", "message": "Try this please"},
    )
    assert response.status_code == 422


def test_chat_requires_pairing(client):
    response = client.post("/chat", json={"prompt": "سلام"})
    assert response.status_code == 401


def test_latest_update_handles_missing_release(client, monkeypatch):
    class MissingRelease:
        status_code = 404

    monkeypatch.setattr(api.requests, "get", lambda *args, **kwargs: MissingRelease())
    response = client.get("/updates/latest")
    assert response.status_code == 200
    assert response.json()["available"] is False
