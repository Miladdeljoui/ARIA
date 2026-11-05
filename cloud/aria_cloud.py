import base64
import hashlib
import os
import sqlite3
import time
import secrets
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

APP_HOST = os.getenv("ARIA_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("ARIA_PORT", "8000"))
OLLAMA_URL = os.getenv("ARIA_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
# Default to AvalAI: a local-currency, Iran-oriented OpenAI-compatible gateway.
# Provider credentials stay on the server and are never returned to Android.
ARIA_PROVIDER = os.getenv("ARIA_PROVIDER", "avalai").strip().lower()
DEFAULT_CHAT_URLS = {
    "avalai": "https://api.avalai.ir/v1/chat/completions",
    "doona": "https://platform.doona.ai/v1/chat/completions",
    "1xai": "https://1xai.ir/v1/chat/completions",
    "heroai": "https://iranapi.heroai.ir/ai/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
ARIA_API_BASE_URL = os.getenv("ARIA_API_BASE_URL", DEFAULT_CHAT_URLS.get(ARIA_PROVIDER, "")).strip()
ARIA_API_KEY = os.getenv("ARIA_API_KEY", "").strip() or os.getenv("OPENROUTER_API_KEY", "").strip()
DEFAULT_IMAGE_URLS = {
    "avalai": "https://api.avalai.ir/v1/images/generations",
    "doona": "https://platform.doona.ai/v1/images/generations",
}
ARIA_IMAGE_API_URL = os.getenv("ARIA_IMAGE_API_URL", DEFAULT_IMAGE_URLS.get(ARIA_PROVIDER, "")).strip()
ARIA_IMAGE_API_KEY = os.getenv("ARIA_IMAGE_API_KEY", "").strip() or ARIA_API_KEY
ARIA_VIDEO_API_URL = os.getenv("ARIA_VIDEO_API_URL", "https://api.avalai.ir/v1/videos").strip()
ARIA_VIDEO_API_KEY = os.getenv("ARIA_VIDEO_API_KEY", "").strip() or ARIA_API_KEY
VIDEO_TIMEOUT_SECONDS = max(60, min(330, int(os.getenv("ARIA_VIDEO_TIMEOUT_SECONDS", "300"))))
VIDEO_POLL_SECONDS = max(3, min(15, int(os.getenv("ARIA_VIDEO_POLL_SECONDS", "5"))))
OWNER_EMAIL = os.getenv("ARIA_OWNER_EMAIL", "miladdeljoui22@gmail.com").strip().lower()
TRIAL_DAYS = max(0, min(365, int(os.getenv("ARIA_TRIAL_DAYS", "30"))))
MONTHLY_PRICE_TOMAN = max(0, int(os.getenv("ARIA_MONTHLY_PRICE_TOMAN", "99000")))
ZARINPAL_SANDBOX = os.getenv("ZARINPAL_SANDBOX", "true").strip().lower() in {"1", "true", "yes", "on"}
ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID", "").strip()
ZARINPAL_BASE_URL = "https://sandbox.zarinpal.com" if ZARINPAL_SANDBOX else "https://payment.zarinpal.com"
ZARINPAL_STARTPAY_BASE = "https://sandbox.zarinpal.com/pg/StartPay" if ZARINPAL_SANDBOX else "https://www.zarinpal.com/pg/StartPay"
ARIA_PUBLIC_BASE_URL = os.getenv("ARIA_PUBLIC_BASE_URL", "").strip().rstrip("/")
GITHUB_RELEASES_URL = os.getenv("ARIA_GITHUB_RELEASES_URL", "https://api.github.com/repos/Miladdeljoui/ARIA/releases/latest")
DEFAULT_REMOTE_MODEL = {
    # AvalAI's current DeepSeek V4.1 Flash alias. Keep the model override
    # server-side via ARIA_MODEL; never assume a legacy model ID is permanent.
    "avalai": "deepseek-flash",
    "doona": "gemini-3.5-flash-lite",
    "1xai": "deepseek-chat",
    "heroai": "deepseek/deepseek-chat",
    "openrouter": "openrouter/free",
}.get(ARIA_PROVIDER, "qwen3:1.7b")
MODEL = os.getenv("ARIA_MODEL", "").strip() or (DEFAULT_REMOTE_MODEL if ARIA_API_KEY else "qwen3:1.7b")
ARIA_MEDIA_ENABLED = os.getenv("ARIA_MEDIA_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
ARIA_IMAGE_MODEL = os.getenv(
    "ARIA_IMAGE_MODEL",
    "muse-image-1.0" if ARIA_PROVIDER == "avalai" else ("gpt-image-2" if ARIA_PROVIDER == "doona" else ""),
).strip()
ARIA_VIDEO_MODEL = os.getenv("ARIA_VIDEO_MODEL", "veo-3.1-fast-generate-001").strip()
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
    duration: int = Field(default=4, ge=4, le=8)
    aspect_ratio: str = Field(default="16:9", pattern=r"^(16:9|9:16)$")


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
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            authority TEXT NOT NULL UNIQUE,
            amount_rial INTEGER NOT NULL,
            status TEXT NOT NULL,
            ref_id TEXT,
            created_at INTEGER NOT NULL,
            verified_at INTEGER
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


def subscription_access(device_id: int, now: int | None = None) -> tuple[bool, dict]:
    current = int(now or time.time())
    with closing(db()) as connection:
        device = connection.execute(
            "SELECT created_at FROM devices WHERE id = ?", (device_id,)
        ).fetchone()
        if not device:
            return False, {}
        started_at = int(device[0])
        connection.execute(
            """INSERT OR IGNORE INTO subscriptions(device_id, trial_started_at, paid_until)
               VALUES (?, ?, 0)""",
            (device_id, started_at),
        )
        row = connection.execute(
            "SELECT trial_started_at, paid_until FROM subscriptions WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        connection.commit()
    trial_started_at, paid_until = int(row[0]), int(row[1])
    trial_ends_at = trial_started_at + TRIAL_DAYS * 86400
    trial_active = current < trial_ends_at
    paid_active = current < paid_until
    return (trial_active or paid_active), {
        "status": "paid" if paid_active else ("trial" if trial_active else "expired"),
        "trial_days": TRIAL_DAYS,
        "trial_started_at": trial_started_at,
        "trial_ends_at": trial_ends_at,
        "paid_until": paid_until,
        "monthly_price_toman": MONTHLY_PRICE_TOMAN,
        "payment_enabled": bool(ZARINPAL_MERCHANT_ID and ARIA_PUBLIC_BASE_URL.startswith("https://")),
        "payment": (
            ("zarinpal_sandbox" if ZARINPAL_SANDBOX else "zarinpal_live")
            if ZARINPAL_MERCHANT_ID and ARIA_PUBLIC_BASE_URL.startswith("https://")
            else "not_configured"
        ),
        "access_granted": trial_active or paid_active,
    }


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


def hosted_chat_request(messages: list[dict]) -> requests.Response:
    """Call the configured OpenAI-compatible provider.

    AvalAI documents two domestic API hostnames. If DNS/connection setup for
    the primary hostname fails before a response is received, retry the same
    request at the documented domestic fallback. Never retry HTTP errors or
    read timeouts: the provider may already have accepted and billed a request.
    """
    if not ARIA_API_BASE_URL or not ARIA_API_KEY:
        raise RuntimeError("hosted_ai_not_configured")

    urls = [ARIA_API_BASE_URL]
    if ARIA_PROVIDER == "avalai":
        fallback = ARIA_API_BASE_URL.replace("api.avalai.ir", "api.avalapis.ir")
        if fallback != ARIA_API_BASE_URL:
            urls.append(fallback)

    last_error = None
    for endpoint in urls:
        try:
            return requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {ARIA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "stream": False,
                },
                timeout=(12, 90),
            )
        except (requests.ConnectionError, requests.ConnectTimeout) as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("hosted_ai_unavailable")


def ask_hosted_api(messages: list[dict]) -> str:
    response = hosted_chat_request(messages)
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") or []
    answer = choices[0].get("message", {}).get("content", "") if choices else ""
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
        "api_provider": ARIA_PROVIDER if hosted_ai_configured() else "none",
        "api_model": MODEL,
        "anonymous_guest_access": True,
        "media_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_IMAGE_API_KEY or ARIA_VIDEO_API_KEY),
        "image_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_IMAGE_API_KEY and ARIA_IMAGE_API_URL and ARIA_IMAGE_MODEL),
        "video_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_VIDEO_API_KEY and ARIA_VIDEO_API_URL and ARIA_VIDEO_MODEL),
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
        "api_provider": ARIA_PROVIDER if hosted_ai_configured() else "none",
        "api_model": MODEL,
        "anonymous_guest_access": True,
        "media_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_IMAGE_API_KEY or ARIA_VIDEO_API_KEY),
        "image_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_IMAGE_API_KEY and ARIA_IMAGE_API_URL and ARIA_IMAGE_MODEL),
        "video_enabled": ARIA_MEDIA_ENABLED and bool(ARIA_VIDEO_API_KEY and ARIA_VIDEO_API_URL and ARIA_VIDEO_MODEL),
        "ai_provider": ARIA_PROVIDER if hosted_ai_configured() else ("ollama" if ollama_ok else "not_configured"),
        "chat_ready": hosted_ai_configured() or ollama_ok,
        "image_model": ARIA_IMAGE_MODEL,
        "video_model": ARIA_VIDEO_MODEL,
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
    device_id = device_id_from_token(x_aria_token)
    if device_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    _, snapshot = subscription_access(device_id)
    snapshot["owner_email_verification"] = "not_implemented"
    return snapshot


@app.post("/billing/request")
def create_billing_request(x_aria_token: str = Header(default="")):
    device_id = device_id_from_token(x_aria_token)
    if device_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    if not ZARINPAL_MERCHANT_ID or not ARIA_PUBLIC_BASE_URL.startswith("https://"):
        raise HTTPException(status_code=503, detail="payment_not_configured")
    if MONTHLY_PRICE_TOMAN < 1000:
        raise HTTPException(status_code=503, detail="invalid_subscription_price")

    now = int(time.time())
    amount_rial = MONTHLY_PRICE_TOMAN * 10

    # Reuse a pending request for this device for one hour to avoid duplicate invoices.
    with closing(db()) as connection:
        pending = connection.execute(
            """SELECT authority, created_at FROM payments
               WHERE device_id = ? AND status = 'pending' AND created_at > ?
               ORDER BY id DESC LIMIT 1""",
            (device_id, now - 3600),
        ).fetchone()
    if pending:
        authority = str(pending[0])
        return {
            "payment_url": f"{ZARINPAL_STARTPAY_BASE}/{authority}",
            "authority": authority,
            "amount_toman": MONTHLY_PRICE_TOMAN,
            "reused_pending_request": True,
        }

    callback_url = ARIA_PUBLIC_BASE_URL + "/billing/callback"
    request_body = {
        "merchant_id": ZARINPAL_MERCHANT_ID,
        "amount": amount_rial,
        "callback_url": callback_url,
        "description": "اشتراک یک‌ماهه دستیار ARIA",
        "metadata": {},
    }
    try:
        response = requests.post(
            ZARINPAL_BASE_URL + "/pg/v4/payment/request.json",
            json=request_body,
            headers={"Content-Type": "application/json", "User-Agent": "ARIA-Cloud/1.0"},
            timeout=(10, 25),
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=502, detail="payment_gateway_unavailable") from exc

    data = payload.get("data") or {}
    authority = str(data.get("authority", "")).strip()
    if int(data.get("code", -1)) != 100 or not authority:
        errors = payload.get("errors") or {}
        gateway_message = (
            errors.get("message", data.get("message", "unknown"))
            if isinstance(errors, dict)
            else str(errors or data.get("message", "unknown"))
        )
        raise HTTPException(
            status_code=502,
            detail="payment_request_rejected",
            headers={"X-ARIA-Payment-Error": str(gateway_message)[:160]},
        )

    with closing(db()) as connection:
        connection.execute(
            """INSERT INTO payments(device_id, authority, amount_rial, status, created_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (device_id, authority, amount_rial, now),
        )
        connection.commit()

    return {
        "payment_url": f"{ZARINPAL_STARTPAY_BASE}/{authority}",
        "authority": authority,
        "amount_toman": MONTHLY_PRICE_TOMAN,
        "reused_pending_request": False,
    }


@app.get("/billing/callback", response_class=HTMLResponse)
def zarinpal_callback(Authority: str = "", Status: str = ""):
    authority = Authority.strip()
    if not authority:
        return HTMLResponse("<h2>درخواست پرداخت نامعتبر است.</h2>", status_code=400)

    with closing(db()) as connection:
        payment = connection.execute(
            "SELECT id, device_id, amount_rial, status FROM payments WHERE authority = ?",
            (authority,),
        ).fetchone()
    if not payment:
        return HTMLResponse("<h2>تراکنش در ARIA پیدا نشد.</h2>", status_code=404)

    payment_id, device_id, amount_rial, payment_state = payment
    if payment_state == "paid":
        return HTMLResponse("<h2>پرداخت قبلاً تأیید شده است. به برنامه ARIA برگرد.</h2>")

    if Status.strip().upper() != "OK":
        with closing(db()) as connection:
            connection.execute(
                "UPDATE payments SET status = 'cancelled' WHERE id = ? AND status = 'pending'",
                (payment_id,),
            )
            connection.commit()
        return HTMLResponse("<h2>پرداخت لغو شد. اشتراک فعال نشد.</h2>")

    verify_body = {
        "merchant_id": ZARINPAL_MERCHANT_ID,
        "amount": int(amount_rial),
        "authority": authority,
    }
    if not ZARINPAL_MERCHANT_ID:
        return HTMLResponse("<h2>درگاه پرداخت هنوز در سرور پیکربندی نشده است.</h2>", status_code=503)
    try:
        response = requests.post(
            ZARINPAL_BASE_URL + "/pg/v4/payment/verify.json",
            json=verify_body,
            headers={"Content-Type": "application/json", "User-Agent": "ARIA-Cloud/1.0"},
            timeout=(10, 25),
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return HTMLResponse(
            "<h2>بررسی پرداخت موقتاً ناموفق بود. دوباره پرداخت نکن؛ صفحه را بعداً بازخوانی یا با پشتیبانی تماس بگیر.</h2>",
            status_code=503,
        )

    data = payload.get("data") or {}
    verify_code = int(data.get("code", -1))
    if verify_code not in (100, 101):
        with closing(db()) as connection:
            connection.execute(
                "UPDATE payments SET status = 'failed' WHERE id = ? AND status = 'pending'",
                (payment_id,),
            )
            connection.commit()
        return HTMLResponse("<h2>تأیید پرداخت ناموفق بود؛ اشتراک فعال نشد.</h2>", status_code=400)

    now = int(time.time())
    ref_id = str(data.get("ref_id", ""))
    with closing(db()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT status FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()
        if current and current[0] != "paid":
            connection.execute(
                """INSERT OR IGNORE INTO subscriptions(device_id, trial_started_at, paid_until)
                   SELECT id, created_at, 0 FROM devices WHERE id = ?""",
                (device_id,),
            )
            subscription_row = connection.execute(
                "SELECT paid_until, trial_started_at FROM subscriptions WHERE device_id = ?",
                (device_id,),
            ).fetchone()
            old_paid_until = int(subscription_row[0]) if subscription_row else 0
            trial_ends_at = (
                int(subscription_row[1]) + TRIAL_DAYS * 86400
                if subscription_row else now
            )
            new_paid_until = max(now, old_paid_until, trial_ends_at) + 30 * 86400
            connection.execute(
                "UPDATE subscriptions SET paid_until = ? WHERE device_id = ?",
                (new_paid_until, device_id),
            )
            connection.execute(
                "UPDATE payments SET status = 'paid', ref_id = ?, verified_at = ? WHERE id = ?",
                (ref_id, now, payment_id),
            )
        connection.commit()

    return HTMLResponse("<h2>پرداخت با موفقیت تأیید شد. اشتراک ARIA فعال شد؛ به برنامه برگرد و وضعیت اشتراک را تازه‌سازی کن.</h2>")


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
    has_access, subscription_state = subscription_access(device_id)
    if not has_access:
        raise HTTPException(status_code=402, detail="subscription_required")

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
    daily_device_limit = 100 if subscription_state.get("status") == "paid" else 10
    if int(device_usage) >= daily_device_limit:
        detail = "daily_paid_chat_limit" if daily_device_limit > 10 else "daily_guest_chat_limit"
        raise HTTPException(status_code=429, detail=detail)
    if int(global_usage) >= 250:
        raise HTTPException(status_code=429, detail="daily_service_limit")

    messages = chat_messages(request.prompt, request.history)
    try:
        if hosted_ai_configured():
            answer = ask_hosted_api(messages)
        else:
            try:
                health = requests.get(OLLAMA_URL.replace("/api/chat", "/api/tags"), timeout=3)
                health.raise_for_status()
            except requests.RequestException as exc:
                raise HTTPException(
                    status_code=503,
                    detail="cloud_ai_not_configured",
                ) from exc
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
    provider_key = ARIA_IMAGE_API_KEY if kind == "image" else ARIA_VIDEO_API_KEY
    if not provider_key:
        raise HTTPException(status_code=503, detail=f"{kind}_provider_not_configured")
    device_id = device_id_from_token(token)
    if device_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    has_access, _ = subscription_access(device_id)
    if not has_access:
        raise HTTPException(status_code=402, detail="subscription_required")
    now = int(time.time())
    # Reserve quota atomically before contacting a paid provider. A failed or
    # timed-out upstream request still consumes one attempt to avoid accidental
    # duplicate paid requests on retry.
    with closing(db()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        count = connection.execute(
            "SELECT COUNT(*) FROM media_usage WHERE device_id = ? AND kind = ? AND created_at > ?",
            (device_id, kind, now - 86400),
        ).fetchone()[0]
        global_count = connection.execute(
            "SELECT COUNT(*) FROM media_usage WHERE kind = ? AND created_at > ?",
            (kind, now - 86400),
        ).fetchone()[0]
        # Conservative beta limits protect prepaid provider credit.
        per_device_cap = 1 if kind == "video" else 3
        global_cap = 1 if kind == "video" else 5
        if int(count) >= per_device_cap:
            raise HTTPException(status_code=429, detail=f"daily_{kind}_limit")
        if int(global_count) >= global_cap:
            raise HTTPException(status_code=429, detail=f"daily_service_{kind}_limit")
        connection.execute(
            "INSERT INTO media_usage(device_id, kind, created_at) VALUES (?, ?, ?)",
            (device_id, kind, now),
        )
        connection.commit()
    return device_id


@app.post("/media/image")
def generate_image(payload: ImageRequest, x_aria_token: str = Header(default="")):
    device_id = require_media_access(x_aria_token, "image")
    try:
        response = requests.post(
            ARIA_IMAGE_API_URL,
            headers={
                "Authorization": f"Bearer {ARIA_IMAGE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": ARIA_IMAGE_MODEL,
                "prompt": payload.prompt.strip(),
                "size": "1024x1024",
                "quality": "medium",
                "n": 1,
            },
            timeout=180,
        )
        response.raise_for_status()
        data = response.json().get("data") or []
        if not data:
            raise ValueError("empty_image_response")
        item = data[0]
        image_data = item.get("b64_json")
        mime_type = item.get("mime_type", "image/png")
        if not image_data and item.get("url"):
            image_response = requests.get(item["url"], timeout=90)
            image_response.raise_for_status()
            image_data = base64.b64encode(image_response.content).decode("ascii")
            mime_type = image_response.headers.get("Content-Type", mime_type)
        if not image_data:
            raise ValueError("image_response_missing_data")
        return {
            "model": ARIA_IMAGE_MODEL,
            "mime_type": mime_type,
            "image_base64": image_data,
            "note": "image_generation_may_use_paid_provider_credits",
        }
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", 503)
        raise HTTPException(
            status_code=429 if status_code == 429 else 503,
            detail="image_provider_unavailable_check_model_and_credits",
        ) from exc
    except (ValueError, KeyError, IndexError) as exc:
        raise HTTPException(status_code=503, detail="invalid_image_response") from exc


@app.post("/media/video")
def generate_video(payload: VideoRequest, x_aria_token: str = Header(default="")):
    """Generate a short clip through AvalAI's asynchronous Videos API."""
    device_id = require_media_access(x_aria_token, "video")
    if payload.duration not in (4, 8):
        raise HTTPException(status_code=422, detail="video_duration_must_be_4_or_8_seconds")

    # Do not set Content-Type manually: requests adds the multipart boundary.
    headers = {
        "Authorization": f"Bearer {ARIA_VIDEO_API_KEY}",
    }
    size = {
        "16:9": "1280x720",
        "9:16": "720x1280",
    }[payload.aspect_ratio]

    try:
        create_response = requests.post(
            ARIA_VIDEO_API_URL,
            headers=headers,
            # AvalAI's Videos API expects multipart/form-data, not JSON.
            files={
                "model": (None, ARIA_VIDEO_MODEL),
                "prompt": (None, payload.prompt.strip()),
                "size": (None, size),
                "seconds": (None, str(payload.duration)),
            },
            timeout=60,
        )
        create_response.raise_for_status()
        job = create_response.json()
        video_id = str(job.get("id", "")).strip()
        if not video_id:
            raise ValueError("video_job_id_missing")

        deadline = time.monotonic() + VIDEO_TIMEOUT_SECONDS
        state = str(job.get("status", "queued")).lower()
        while state not in {"completed", "failed"} and time.monotonic() < deadline:
            time.sleep(VIDEO_POLL_SECONDS)
            poll_response = requests.get(
                f"{ARIA_VIDEO_API_URL.rstrip('/')}/{quote(video_id, safe='')}",
                headers={"Authorization": f"Bearer {ARIA_VIDEO_API_KEY}"},
                timeout=30,
            )
            poll_response.raise_for_status()
            job = poll_response.json()
            state = str(job.get("status", "")).lower()

        if state == "failed":
            raise HTTPException(status_code=502, detail="video_generation_failed_no_retry_until_checked")
        if state != "completed":
            # Avoid duplicate paid jobs if the upstream render is still running.
            raise HTTPException(status_code=504, detail="video_generation_still_processing_check_provider_before_retry")

        content_response = requests.get(
            f"{ARIA_VIDEO_API_URL.rstrip('/')}/{quote(video_id, safe='')}/content",
            headers={"Authorization": f"Bearer {ARIA_VIDEO_API_KEY}"},
            timeout=90,
        )
        content_response.raise_for_status()
        content_type = content_response.headers.get("Content-Type", "video/mp4")
        if "json" in content_type.lower() or not content_response.content:
            raise ValueError("empty_or_invalid_video_content")
        if len(content_response.content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="video_file_too_large")

        return {
            "model": ARIA_VIDEO_MODEL,
            "job_id": video_id,
            "mime_type": content_type,
            "video_base64": base64.b64encode(content_response.content).decode("ascii"),
            "note": "video_generation_uses_provider_credits",
        }
    except HTTPException:
        raise
    except requests.RequestException as exc:
        upstream_status = getattr(getattr(exc, "response", None), "status_code", 503)
        code = 429 if upstream_status == 429 else (402 if upstream_status == 402 else 503)
        raise HTTPException(
            status_code=code,
            detail="video_provider_unavailable_check_model_and_credits",
        ) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="invalid_video_response") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
