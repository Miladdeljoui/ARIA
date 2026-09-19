import hashlib
import json
import os
import secrets
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

import requests

HOST = os.getenv("ARIA_HOST", "0.0.0.0")
PORT = int(os.getenv("ARIA_PORT", "8765"))
OLLAMA_URL = os.getenv("ARIA_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_TAGS_URL = os.getenv("ARIA_OLLAMA_TAGS_URL", "http://127.0.0.1:11434/api/tags")
MODEL = os.getenv("ARIA_MODEL", "qwen3:1.7b")
OWNER_NAME = os.getenv("ARIA_OWNER_NAME", "Milad")
STATE_FILE = Path(os.getenv("ARIA_STATE_FILE", "aria_state.json"))

STATE_LOCK = Lock()


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_state() -> dict:
    with STATE_LOCK:
        if not STATE_FILE.exists():
            return {}
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}


def save_state(state: dict) -> None:
    with STATE_LOCK:
        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def ensure_state() -> dict:
    state = load_state()
    changed = False

    if "pairing_code_hash" not in state:
        pairing_code = f"{secrets.randbelow(1_000_000):06d}"
        state["pairing_code_hash"] = sha256(pairing_code)
        state["pairing_code_display"] = pairing_code
        state["created_at"] = int(time.time())
        state["owner_name"] = OWNER_NAME
        state["devices"] = []
        changed = True

    state.setdefault("owner_name", OWNER_NAME)
    state.setdefault("devices", [])

    if changed:
        save_state(state)

    return state


def ollama_available() -> bool:
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=3)
        return response.ok
    except requests.RequestException:
        return False


def internet_available(timeout: float = 2.0) -> bool:
    try:
        sock = socket.create_connection(("1.1.1.1", 53), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def ask_local(prompt: str) -> tuple[str, dict]:\n    decision = classify_request(prompt)\n    memories = MEMORY.search(prompt, limit=5)\n    recent = MEMORY.recent_conversation(limit=12)\n\n    memory_text = "\n".join(\n        f"- {item['content']}" for item in memories\n    ) or "- مورد مرتبطی در حافظه پیدا نشد."\n\n    context_text = "\n".join(\n        f"{item['role']}: {item['content']}" for item in recent\n    )\n\n    system = (\n        f"تو ARIA هستی، دستیار شخصی {OWNER_NAME} و پروژه‌ای که او ساخته است. "\n        "فارسی پاسخ بده مگر اینکه کاربر زبان دیگری بخواهد. "\n        "برای کارهای حساس، مالی، مخرب یا تغییرات واقعی، بدون تأیید مالک اقدام نکن. "\n        "در این نسخه ابزار اجرایی فعال نیست و فقط پاسخ متنی و تحلیل ارائه می‌کنی.\n\n"\n        f"سطح مجوز درخواست فعلی: {decision.level.value}. "\n        f"دلیل: {decision.reason}\n\n"\n        "حافظه مرتبط:\n"\n        f"{memory_text}\n\n"\n        "گفت‌وگوی اخیر:\n"\n        f"{context_text}"\n    )\n\n    response = requests.post(\n        OLLAMA_URL,\n        json={\n            "model": MODEL,\n            "messages": [\n                {"role": "system", "content": system},\n                {"role": "user", "content": prompt},\n            ],\n            "stream": False,\n        },\n        timeout=120,\n    )\n    response.raise_for_status()\n\n    answer = response.json()["message"]["content"]\n    return answer, {\n        "level": decision.level.value,\n        "requires_approval": decision.requires_approval,\n        "reason": decision.reason,\n    }
