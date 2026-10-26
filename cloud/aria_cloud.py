import hashlib
import os
import sqlite3
import time
import secrets
from contextlib import closing
from pathlib import Path

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

APP_HOST = os.getenv("ARIA_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("ARIA_PORT", "8000"))
OLLAMA_URL = os.getenv("ARIA_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
# Configure an OpenAI-compatible hosted inference endpoint to run ARIA without a laptop.
# Example endpoint: https://openrouter.ai/api/v1/chat/completions
ARIA_API_BASE_URL = os.getenv("ARIA_API_BASE_URL", "https://openrouter.ai/api/v1/chat/completions").strip()
ARIA_API_KEY = os.getenv("ARIA_API_KEY", os.getenv("OPENROUTER_API_KEY", "")).strip()
OWNER_EMAIL = os.getenv("ARIA_OWNER_EMAIL", "miladdeljoui22@gmail.com").strip().lower()
TRIAL_DAYS = max(0, min(365, int(os.getenv("ARIA_TRIAL_DAYS", "30"))))
MONTHLY_PRICE_TOMAN = max(0, int(os.getenv("ARIA_MONTHLY_PRICE_TOMAN", "99000")))
GITHUB_RELEASES_URL = os.getenv("ARIA_GITHUB_RELEASES_URL", "https://api.github.com/repos/Miladdeljoui/ARIA/releases/latest")
MODEL = os.getenv("ARIA_MODEL", "").strip() or ("openrouter/free" if ARIA_API_KEY else "qwen3:1.7b")
if ARIA_API_KEY and MODEL == "qwen3:1.7b":
    MODEL = "openrouter/free"
ARIA_MEDIA_ENABLED = os.getenv("ARIA_MEDIA_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
ARIA_IMAGE_MODEL = os.getenv("ARIA_IMAGE_MODEL", "bytedance-seed/seedream-4.5").strip()
ARIA_VIDEO_MODEL = os.getenv("ARIA_VIDEO_MODEL", "bytedance/seedance-2.0").strip()
OWNER_NAME = os.getenv("ARIA_OWNER_NAME", "Milad")
DB_PATH = Path(os.getenv("ARIA_DB", "aria_cloud.db"))

app = FastAPI(title="ARIA Cloud", version="0.4.0")


class GuestRequest(BaseModel):
    client_id: str = Field(min_length=16, max_length=100)
    device_name: str = Field(default="Android guest", max_length=80)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    history: list[dict] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    category: str = Field(default="general", min_length=1, max_length=40)
    message: str = Field(min_length=3, max_length=4000)
    app_version: str = Field(default="unknown", max_length=40)


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)


class VideoRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)
    duration: int = Field(default=5, ge=3, le=8)
    aspect_ratio: str = Field(default="16:9", pattern=r"^(16:9|9:16|1:1)$")


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_installations (
            install_hash TEXT PRIMARY KEY,
            device_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            last_seen INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS guest_registration_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS media_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
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
        "anonymous_guest_access": True,
        "media_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_API_KEY),
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
        "anonymous_guest_access": True,
        "media_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_API_KEY),
        "ai_provider": "openrouter" if hosted_ai_configured() else "ollama",
        "server_time": int(time.time()),
    }


@app.post("/guest")
def guest(payload: GuestRequest, request: Request):
    """Issue a per-install anonymous token; no pairing code or email is required."""
    now = int(time.time())
    install_hash = sha256(payload.client_id.strip())
    ip_value = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-real-ip")
        or (request.client.host if request.client else "unknown")
    ).strip()
    ip_hash = sha256("aria-guest:" + ip_value)
    token = secrets.token_urlsafe(32)

    with closing(db()) as connection:
        existing = connection.execute(
            "SELECT device_id FROM guest_installations WHERE install_hash = ?",
            (install_hash,),
        ).fetchone()

        if existing:
            device_id = int(existing[0])
            connection.execute(
                "UPDATE guest_installations SET last_seen = ? WHERE install_hash = ?",
                (now, install_hash),
            )
            connection.execute(
                "UPDATE devices SET token_hash = ? WHERE id = ?",
                (sha256(token), device_id),
            )
        else:
            recent = connection.execute(
                "SELECT COUNT(*) FROM guest_registration_events WHERE ip_hash = ? AND created_at > ?",
                (ip_hash, now - 86400),
            ).fetchone()[0]
            if int(recent) >= 10:
                raise HTTPException(
                    status_code=429,
                    detail="guest_registration_limit",
                )
            cursor = connection.execute(
                "INSERT INTO devices(device_name, token_hash, created_at) VALUES (?, ?, ?)",
                (payload.device_name.strip() or "Android guest", sha256(token), now),
            )
            device_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO guest_installations(install_hash, device_id, created_at, last_seen) VALUES (?, ?, ?, ?)",
                (install_hash, device_id, now, now),
            )
            connection.execute(
                "INSERT INTO guest_registration_events(ip_hash, created_at) VALUES (?, ?)",
                (ip_hash, now),
            )

        connection.execute(
            "INSERT OR IGNORE INTO subscriptions(device_id, trial_started_at, paid_until) VALUES (?, ?, 0)",
            (device_id, now),
        )
        connection.commit()

    return {
        "assistant": "ARIA",
        "owner": OWNER_NAME,
        "token": token,
        "plan": "free_beta",
        "daily_chat_limit": 10,
        "media_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_API_KEY),
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

    now = int(time.time())
    with closing(db()) as connection:
        device_usage = connection.execute(
            "SELECT COUNT(*) FROM messages WHERE device_id = ? AND role = 'user' AND created_at > ?",
            (device_id, now - 86400),
        ).fetchone()[0]
        global_usage = connection.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'user' AND created_at > ?",
            (now - 86400,),
        ).fetchone()[0]
    if int(device_usage) >= 10:
        raise HTTPException(status_code=429, detail="daily_guest_chat_limit")
    if int(global_usage) >= 45:
        raise HTTPException(status_code=429, detail="daily_service_limit")

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


def require_media_access(token: str, kind: str) -> int:
    if not ARIA_MEDIA_ENABLED:
        raise HTTPException(status_code=503, detail="media_generation_disabled_by_server")
    if not ARIA_API_KEY:
        raise HTTPException(status_code=503, detail="hosted_ai_not_configured")
    device_id = device_id_from_token(token)
    if device_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    now = int(time.time())
    with closing(db()) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM media_usage WHERE device_id = ? AND kind = ? AND created_at > ?",
            (device_id, kind, now - 86400),
        ).fetchone()[0]
        global_count = connection.execute(
            "SELECT COUNT(*) FROM media_usage WHERE kind = ? AND created_at > ?",
            (kind, now - 86400),
        ).fetchone()[0]
    per_device_cap = 1 if kind == "video" else 3
    global_cap = 8 if kind == "video" else 30
    if int(count) >= per_device_cap:
        raise HTTPException(status_code=429, detail=f"daily_{kind}_limit")
    if int(global_count) >= global_cap:
        raise HTTPException(status_code=429, detail=f"daily_service_{kind}_limit")
    return device_id


def record_media_use(device_id: int, kind: str) -> None:
    with closing(db()) as connection:
        connection.execute(
            "INSERT INTO media_usage(device_id, kind, created_at) VALUES (?, ?, ?)",
            (device_id, kind, int(time.time())),
        )
        connection.commit()


@app.post("/media/image")
def generate_image(payload: ImageRequest, x_aria_token: str = Header(default="")):
    device_id = require_media_access(x_aria_token, "image")
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/images",
            headers={
                "Authorization": f"Bearer {ARIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": ARIA_IMAGE_MODEL, "prompt": payload.prompt.strip()},
            timeout=180,
        )
        response.raise_for_status()
        data = response.json().get("data") or []
        if not data or not data[0].get("b64_json"):
            raise ValueError("empty_image_response")
        record_media_use(device_id, "image")
        return {
            "model": ARIA_IMAGE_MODEL,
            "mime_type": data[0].get("mime_type", "image/png"),
            "image_base64": data[0]["b64_json"],
            "note": "image_generation_may_use_paid_provider_credits",
        }
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", 503)
        raise HTTPException(
            status_code=429 if status_code == 429 else 503,
            detail="image_provider_unavailable_check_model_and_credits",
        ) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="invalid_image_response") from exc


@app.post("/media/video")
def generate_video(payload: VideoRequest, x_aria_token: str = Header(default="")):
    device_id = require_media_access(x_aria_token, "video")
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/videos",
            headers={
                "Authorization": f"Bearer {ARIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": ARIA_VIDEO_MODEL,
                "prompt": payload.prompt.strip(),
                "duration": payload.duration,
                "aspect_ratio": payload.aspect_ratio,
                "generate_audio": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        job = response.json()
        job_id = job.get("id") or job.get("generation_id")
        if not job_id:
            raise ValueError("missing_video_job_id")
        record_media_use(device_id, "video")
        return {
            "id": job_id,
            "status": job.get("status", "pending"),
            "polling_url": f"/media/video/{job_id}",
            "model": ARIA_VIDEO_MODEL,
            "note": "video_generation_may_use_paid_provider_credits",
        }
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", 503)
        raise HTTPException(
            status_code=429 if status_code == 429 else 503,
            detail="video_provider_unavailable_check_model_and_credits",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="invalid_video_response") from exc


@app.get("/media/video/{job_id}")
def video_status(job_id: str, x_aria_token: str = Header(default="")):
    if not ARIA_MEDIA_ENABLED or not ARIA_API_KEY:
        raise HTTPException(status_code=503, detail="media_generation_disabled_by_server")
    if device_id_from_token(x_aria_token) is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    if not job_id or len(job_id) > 200 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in job_id):
        raise HTTPException(status_code=400, detail="invalid_video_job_id")
    try:
        response = requests.get(
            f"https://openrouter.ai/api/v1/videos/{job_id}",
            headers={"Authorization": f"Bearer {ARIA_API_KEY}"},
            timeout=45,
        )
        response.raise_for_status()
        job = response.json()
        return {
            "id": job.get("id", job_id),
            "status": job.get("status", "unknown"),
            "error": job.get("error"),
            "video_urls": job.get("unsigned_urls") or [],
            "usage": job.get("usage"),
        }
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", 503)
        raise HTTPException(
            status_code=429 if status_code == 429 else 503,
            detail="video_status_unavailable",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
