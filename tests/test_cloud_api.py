import pytest
from fastapi.testclient import TestClient

from cloud import aria_cloud as api
from app import app as paas_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(api, "TRIAL_DAYS", 30)
    monkeypatch.setattr(api, "MONTHLY_PRICE_TOMAN", 99000)
    monkeypatch.setattr(api, "ARIA_MEDIA_ENABLED", False)
    return TestClient(api.app)


def guest(client, client_id="test-installation-123456"):
    response = client.post(
        "/guest",
        json={"client_id": client_id, "device_name": "test-phone"},
    )
    assert response.status_code == 200
    return response.json()["token"]


def test_platform_entrypoint_starts_without_pairing_secret():
    response = TestClient(paas_app).get("/status")
    assert response.status_code == 200
    assert response.json()["assistant"] == "ARIA"


def test_home_and_status_are_available(client, monkeypatch):
    monkeypatch.setattr(api, "hosted_ai_configured", lambda: False)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["assistant"] == "ARIA"
    assert response.json()["anonymous_guest_access"] is True
    assert client.get("/status").status_code == 200


def test_guest_registers_without_pairing_code_and_starts_trial(client):
    token = guest(client)
    response = client.get("/subscription", headers={"X-ARIA-Token": token})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "trial"
    assert body["trial_days"] == 30
    assert body["monthly_price_toman"] == 99000
    assert body["access_granted"] is True


def test_guest_reissue_invalidates_old_token_for_same_install(client):
    token1 = guest(client, "stable-install-id-987654321")
    token2 = guest(client, "stable-install-id-987654321")
    assert token1 != token2
    assert client.get("/subscription", headers={"X-ARIA-Token": token1}).status_code == 401
    assert client.get("/subscription", headers={"X-ARIA-Token": token2}).status_code == 200


def test_subscription_requires_valid_token(client):
    response = client.get("/subscription", headers={"X-ARIA-Token": "invalid"})
    assert response.status_code == 401


def test_feedback_requires_token_and_saves_feedback(client):
    unauthorized = client.post(
        "/feedback", json={"category": "idea", "message": "Add dark mode"}
    )
    assert unauthorized.status_code == 401

    token = guest(client)
    response = client.post(
        "/feedback",
        headers={"X-ARIA-Token": token},
        json={"category": "idea", "message": "Add dark mode", "app_version": "0.4.0-beta1"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_feedback_rejects_unknown_category(client):
    token = guest(client)
    response = client.post(
        "/feedback",
        headers={"X-ARIA-Token": token},
        json={"category": "admin", "message": "Try this please"},
    )
    assert response.status_code == 422


def test_chat_rejects_missing_and_invalid_tokens(client):
    assert client.post("/chat", json={"prompt": "سلام"}).status_code == 401
    assert client.post(
        "/chat",
        headers={"X-ARIA-Token": "invalid"},
        json={"prompt": "سلام"},
    ).status_code == 401


def test_chat_daily_device_limit_is_enforced(client):
    token = guest(client)
    device_id = api.device_id_from_token(token)
    now = __import__("time").time()
    with api.db() as connection:
        for index in range(10):
            connection.execute(
                "INSERT INTO messages(device_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
                (device_id, f"test-{index}", int(now)),
            )
        connection.commit()
    response = client.post(
        "/chat",
        headers={"X-ARIA-Token": token},
        json={"prompt": "Should hit the rate limit"},
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "daily_guest_chat_limit"


def test_media_disabled_by_default(client, monkeypatch):
    token = guest(client)
    response = client.post(
        "/media/image",
        headers={"X-ARIA-Token": token},
        json={"prompt": "a blue cat"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "media_generation_disabled_by_server"


def test_latest_update_handles_missing_release(client, monkeypatch):
    class MissingRelease:
        status_code = 404

    monkeypatch.setattr(api.requests, "get", lambda *args, **kwargs: MissingRelease())
    response = client.get("/updates/latest")
    assert response.status_code == 200
    assert response.json()["available"] is False

def test_neta_rz_live_catalogue_and_selected_model_chat(client, monkeypatch):
    monkeypatch.setattr(api, "ARIA_PROVIDER", "netarz")
    monkeypatch.setattr(api, "ARIA_API_BASE_URL", "https://ir.gisoo.pro/api/v1/chat/completions")
    monkeypatch.setattr(api, "ARIA_API_KEY", "test-provider-key")
    monkeypatch.setattr(api, "hosted_ai_configured", lambda: True)
    monkeypatch.setattr(api, "ARIA_MODELS_UNRESTRICTED", True)
    monkeypatch.setattr(api, "LIVE_MODEL_CATALOGUE", [])

    class FakeModelsResponse:
        ok = True

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {"id": "deepseek-flash", "type": "chat"},
                    {"id": "openrouter/anthropic/claude-sonnet-4.5", "type": "chat"},
                ]
            }

    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        return FakeModelsResponse()

    monkeypatch.setattr(api.requests, "get", fake_get)

    token = guest(client, "neta-rz-live-catalogue-install-001")
    models_response = client.get(
        "/models",
        headers={"X-ARIA-Token": token},
    )
    assert models_response.status_code == 200
    assert models_response.json()["models"] == [
        "deepseek-flash",
        "openrouter/anthropic/claude-sonnet-4.5",
    ]
    assert requested_urls[0].endswith("/models?type=chat")

    selected = {}

    def fake_chat(messages, model_override=None):
        selected["model"] = model_override
        return "پاسخ آزمایشی"

    monkeypatch.setattr(api, "ask_hosted_api", fake_chat)
    chat_response = client.post(
        "/chat",
        headers={"X-ARIA-Token": token},
        json={
            "prompt": "سلام",
            "model": "openrouter/anthropic/claude-sonnet-4.5",
        },
    )
    assert chat_response.status_code == 200
    assert chat_response.json()["answer"] == "پاسخ آزمایشی"
    assert selected["model"] == "openrouter/anthropic/claude-sonnet-4.5"

def test_neta_rz_status_checks_authenticated_account_and_balance(client, monkeypatch):
    monkeypatch.setattr(api, "ARIA_PROVIDER", "netarz")
    monkeypatch.setattr(api, "ARIA_API_BASE_URL", "https://ir.gisoo.pro/api/v1/chat/completions")
    monkeypatch.setattr(api, "ARIA_API_KEY", "test-provider-key")
    monkeypatch.setattr(api, "hosted_ai_configured", lambda: True)

    class FakeResponse:
        ok = False

        def __init__(self, payload=None):
            self.payload = payload or {}

        def raise_for_status(self):
            if self.payload.get("raise"):
                raise api.requests.HTTPError("invalid API key")

        def json(self):
            return self.payload

    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        if url.endswith("/api/tags"):
            return FakeResponse()
        if url.endswith("/api/v1/me"):
            return FakeResponse({"status": "active", "balance": {"usd": "0.50"}})
        if url.endswith("/api/v1/models?type=chat"):
            return FakeResponse({"data": [{"id": "deepseek-flash"}]})
        raise AssertionError(f"Unexpected health URL: {url}")

    monkeypatch.setattr(api.requests, "get", fake_get)
    response = client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["provider_connected"] is True
    assert body["chat_ready"] is True
    assert requested_urls[-2:] == [
        "https://ir.gisoo.pro/api/v1/me",
        "https://ir.gisoo.pro/api/v1/models?type=chat",
    ]

