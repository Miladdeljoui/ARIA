import base64
import hashlib
import logging
import os
import sqlite3
import time
import secrets
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

APP_HOST = os.getenv("ARIA_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("ARIA_PORT", "8000"))
OLLAMA_URL = os.getenv("ARIA_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
# Default to AvalAI: a local-currency, Iran-oriented OpenAI-compatible gateway.
# Provider credentials stay on the server and are never returned to Android.
ARIA_PROVIDER = os.getenv("ARIA_PROVIDER", "1xai").strip().lower()
DEFAULT_CHAT_URLS = {
    "1xai": "https://1xai.ir/v1/chat/completions",
    "avalai": "https://api.avalai.ir/v1/chat/completions",
    "doona": "https://platform.doona.ai/v1/chat/completions",
    "1xai": "https://1xai.ir/v1/chat/completions",
    "heroai": "https://iranapi.heroai.ir/ai/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
ARIA_API_BASE_URL = os.getenv("ARIA_API_BASE_URL", DEFAULT_CHAT_URLS.get(ARIA_PROVIDER, "")).strip()
ARIA_API_KEY = os.getenv("ARIA_API_KEY", "").strip() or os.getenv("OPENROUTER_API_KEY", "").strip()
DEFAULT_IMAGE_URLS = {
    "1xai": "https://1xai.ir/v1/images/generations",
    "avalai": "https://api.avalai.ir/v1/images/generations",
    "doona": "https://platform.doona.ai/v1/images/generations",
}
ARIA_IMAGE_API_URL = os.getenv("ARIA_IMAGE_API_URL", DEFAULT_IMAGE_URLS.get(ARIA_PROVIDER, "")).strip()
ARIA_IMAGE_API_KEY = os.getenv("ARIA_IMAGE_API_KEY", "").strip() or ARIA_API_KEY
ARIA_VIDEO_API_URL = os.getenv(
    "ARIA_VIDEO_API_URL",
    "https://api.avalai.ir/v1/videos" if ARIA_PROVIDER == "avalai" else "",
).strip()
ARIA_VIDEO_API_KEY = os.getenv("ARIA_VIDEO_API_KEY", "").strip()
if not ARIA_VIDEO_API_KEY and ARIA_PROVIDER != "1xai":
    ARIA_VIDEO_API_KEY = ARIA_API_KEY
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
    "1xai": "deepseek-v4-flash",
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
    "muse-image-1.0" if ARIA_PROVIDER == "avalai" else ("gpt-image-2" if ARIA_PROVIDER in {"doona", "1xai"} else ""),
).strip()
ARIA_VIDEO_MODEL = os.getenv("ARIA_VIDEO_MODEL", "veo-3.1-fast-generate-001").strip()
OWNER_NAME = os.getenv("ARIA_OWNER_NAME", "Milad")
DB_PATH = Path(os.getenv("ARIA_DB", "aria_cloud.db"))

app = FastAPI(title="ARIA Cloud", version="0.4.1")

logger = logging.getLogger("aria.cloud")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all to avoid leaking stack traces while logging for the owner."""
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "internal_server_error",
            "message": "خطای داخلی سرور. جزئیات فقط در لاگ مالک ثبت شد.",
            "assistant": "ARIA",
        },
    )
