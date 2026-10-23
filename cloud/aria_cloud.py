import hashlib
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP_HOST = os.getenv("ARIA_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("ARIA_PORT", "8000"))
OLLAMA_URL = os.getenv("ARIA_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
# Configure an OpenAI-compatible hosted inference endpoint to run ARIA without a laptop.
# Example endpoint: https://openrouter.ai/api/v1/chat/completions
ARIA_API_BASE_URL = os.getenv("ARIA_API_BASE_URL", "https://openrouter.ai/api/v1/chat/completions").strip()
ARIA_API_KEY = os.getenv("ARIA_API_KEY", "").strip()
OWNER_EMAIL = os.getenv("ARIA_OWNER_EMAIL", "miladdeljoui22@gmail.com").strip().lower()
TRIAL_DAYS = max(0, min(365, int(os.getenv("ARIA_TRIAL_DAYS", "30"))))
MONTHLY_PRICE_TOMAN = max(0, int(os.getenv("ARIA_MONTHLY_PRICE_TOMAN", "99000")))
GITHUB_RELEASES_URL = os.getenv("ARIA_GITHUB_RELEASES_URL", "https://api.github.com/repos/Miladdeljoui/ARIA/releases/latest")
MODEL = os.getenv("ARIA_MODEL", "").strip() or ("openrouter/free" if os.getenv("ARIA_API_KEY", "").strip() else "qwen3:1.7b")
if os.getenv("ARIA_API_KEY", "").strip() and MODEL == "qwen3:1.7b":
    MODEL = "openrouter/free"
OWNER_NAME = os.getenv("ARIA_OWNER_NAME", "Milad")
PAIRING_CODE = os.getenv("ARIA_PAIRING_CODE", "")
DB_PATH = Path(os.getenv("ARIA_DB", "aria_cloud.db"))

app = FastAPI(title="ARIA Cloud", version="0.3.0")


class PairRequest(BaseModel):
    code: str = Field(min_length=6, max_length=64)
    device_name: str = Field(default="Android", max_length=80)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    history: list[dict] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    category: str = Field(default="general", min_length=1, max_length=40)
    message: str = Field(min_length=3, max_length=4000)
    app_version: str = Field(default="unknown", max_length=40)


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            device_id INTEGER PRIMARY KEY,
            trial_started_at INTEGER NOT NULL,
            paid_until INTEGER NOT NULL DEFAULT 0,
            owner_email TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            message TEXT NOT NULL,
            app_version TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_pair_code() -> None:
    if not PAIRING_CODE or len(PAIRING_CODE) < 6:
        raise RuntimeError(
            "ARIA_PAIRING_CODE must be set to a secret value with at least 6 characters"
        )

    with closing(db()) as connection:
        connection.execute(
            """
            INSERT INTO settings(key, value)
            VALUES('pairing_code', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (sha256(PAIRING_CODE),),
        )
        connection.commit()


def device_id_from_token(token: str) -> int | None:
    if not token:
        return None
    token_hash = sha256(token)
    with closing(db()) as connection:
        row = connection.execute(
            "SELECT id FROM devices WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        return int(row[0]) if row else None


def system_message() -> dict:
    return {
        "role": "system",
        "content": (
            f"تو ARIA هستی، دستیار شخصی {OWNER_NAME} و پروژه‌ای که او ساخته است. "
            "فارسی پاسخ بده مگر اینکه کاربر زبان دیگری بخواهد. "
            "هرگز ادعا نکن عملی را انجام داده‌ای مگر اینکه ابزار آن واقعاً اجرا شده باشد. "
            "برای اقدام حساس، حذف اطلاعات، تغییر امنیت، پرداخت، انتشار یا ارتباط بیرونی "
            "به تأیید مالک نیاز است."
        ),
    }


def chat_messages(prompt: str, history: list[dict]) -> list[dict]:
    # Keep only valid conversational roles and string content from client history.
    safe_history = []
    for item in history[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            safe_history.append({"role": role, "content": content[:12000]})
    return [system_message(), *safe_history, {"role": "user", "content": prompt}]


def ask_hosted_api(messages: list[dict]) -> str:
    if not ARIA_API_BASE_URL or not ARIA_API_KEY:
        raise RuntimeError("hosted_ai_not_configured")
    response = requests.post(
        ARIA_API_BASE_URL,
        headers={
            "Authorization": f"Bearer {ARIA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "stream": False,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    answer = payload["choices"][0]["message"]["content"]
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("empty_model_response")
    return answer.strip()


def ask_ollama(messages: list[dict]) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "messages": messages, "stream": False},
        timeout=90,
    )
    response.raise_for_status()
    answer = response.json()["message"]["content"]
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("empty_model_response")
    return answer.strip()


def hosted_ai_configured() -> bool:
    return bool(ARIA_API_BASE_URL and ARIA_API_KEY)


@app.get("/")
def home():
    return {
        "assistant": "ARIA",
        "status": "online",
        "health": "/status",
        "chat": "/chat",
        "cloud_ai_configured": hosted_ai_configured(),
    }


@app.get("/status")
def status():
    ollama_ok = False
    try:
        response = requests.get(
            OLLAMA_URL.replace("/api/chat", "/api/tags"),
            timeout=2,
        )
        ollama_ok = response.ok
    except requests.RequestException:
        pass

    return {
        "assistant": "ARIA",
        "owner": OWNER_NAME,
        "model": MODEL,
        "cloud": True,
        "ollama": ollama_ok,
        "cloud_ai_configured": hosted_ai_configured(),
        "ai_provider": "openai-compatible" if hosted_ai_configured() else "ollama",
        "server_time": int(time.time()),
    }


@app.post("/pair")
def pair(request: PairRequest):
    with closing(db()) as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = 'pairing_code'"
        ).fetchone()

        if not row or sha256(request.code.strip()) != row[0]:
            raise HTTPException(status_code=401, detail="invalid_pairing_code")

        token = __import__("secrets").token_urlsafe(32)
        connection.execute(
            """
            INSERT INTO devices(device_name, token_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (request.device_name.strip() or "Android", sha256(token), int(time.time())),
        )
        connection.commit()

    return {
        "assistant": "ARIA",
        "owner": OWNER_NAME,
        "token": token,
    }


@app.get("/subscription")
def subscription(x_aria_token: str = Header(default="")):
    """Server-calculated trial status. Owner exemption waits for verified Google identity."""
    device_id = device_id_from_token(x_aria_token)
    if device_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    now = int(time.time())
    with closing(db()) as connection:
        device = connection.execute(
            "SELECT created_at FROM devices WHERE id = ?", (device_id,)
        ).fetchone()
        connection.execute(
            """INSERT OR IGNORE INTO subscriptions(device_id, trial_started_at, paid_until)
               VALUES (?, ?, 0)""",
            (device_id, int(device[0]) if device else now),
        )
        row = connection.execute(
            "SELECT trial_started_at, paid_until FROM subscriptions WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        connection.commit()
    started, paid_until = int(row[0]), int(row[1])
    trial_end = started + TRIAL_DAYS * 86400
    trial_active = now < trial_end
    paid_active = now < paid_until
    return {
        "status": "paid" if paid_active else ("trial" if trial_active else "expired"),
        "trial_days": TRIAL_DAYS,
        "trial_started_at": started,
        "trial_ends_at": trial_end,
        "paid_until": paid_until,
        "monthly_price_toman": MONTHLY_PRICE_TOMAN,
        "owner_email_verification": "not_implemented",
        "payment": "zarinpal_sandbox_not_implemented",
        "access_granted": paid_active or trial_active,
    }


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest, x_aria_token: str = Header(default="")):
    device_id = device_id_from_token(x_aria_token)
    if device_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    category = request.category.strip().lower()
    if category not in {"bug", "idea", "general", "other"}:
        raise HTTPException(status_code=422, detail="invalid_feedback_category")
    with closing(db()) as connection:
        connection.execute(
            """INSERT INTO feedback(device_id, category, message, app_version, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (device_id, category, request.message.strip(), request.app_version.strip(), int(time.time())),
        )
        connection.commit()
    return {"ok": True, "message": "feedback_received"}


@app.get("/updates/latest")
def latest_update():
    """Return public GitHub Release metadata; this does not install an APK."""
    try:
        response = requests.get(
            GITHUB_RELEASES_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "ARIA-Android"},
            timeout=8,
        )
        if response.status_code == 404:
            return {"available": False, "reason": "no_public_release_yet"}
        response.raise_for_status()
        release = response.json()
        assets = [
            {"name": item.get("name", ""), "url": item.get("browser_download_url", "")}
            for item in release.get("assets", [])
            if str(item.get("name", "")).lower().endswith(".apk")
        ]
        return {
            "available": bool(assets),
            "tag": release.get("tag_name", ""),
            "name": release.get("name", ""),
            "published_at": release.get("published_at", ""),
            "release_url": release.get("html_url", ""),
            "apk_assets": assets,
            "auto_install": False,
        }
    except (requests.RequestException, ValueError):
        raise HTTPException(status_code=503, detail="update_check_unavailable")


@app.post("/chat")
def chat(
    request: ChatRequest,
    x_aria_token: str = Header(default=""),
):
    device_id = device_id_from_token(x_aria_token)
    if device_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")

    messages = chat_messages(request.prompt, request.history)
    try:
        if hosted_ai_configured():
            answer = ask_hosted_api(messages)
        else:
            answer = ask_ollama(messages)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="cloud_ai_not_configured",
        ) from exc
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="ai_provider_unavailable_or_invalid_response",
        ) from exc

    now = int(time.time())
    with closing(db()) as connection:
        connection.execute(
            "INSERT INTO messages(device_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (device_id, "user", request.prompt, now),
        )
        connection.execute(
            "INSERT INTO messages(device_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (device_id, "assistant", answer, now),
        )
        connection.commit()

    return {
        "answer": answer,
        "model": MODEL,
        "cloud": True,
    }


if __name__ == "__main__":
    import uvicorn

    ensure_pair_code()
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
