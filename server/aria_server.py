import hashlib
import json
import os
import secrets
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory import MemoryStore
from core.permissions import classify_request
from core.runtime import internet_available

HOST = os.getenv("ARIA_HOST", "0.0.0.0")
PORT = int(os.getenv("ARIA_PORT", "8765"))
OLLAMA_URL = os.getenv("ARIA_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_TAGS_URL = os.getenv("ARIA_OLLAMA_TAGS_URL", "http://127.0.0.1:11434/api/tags")
MODEL = os.getenv("ARIA_MODEL", "qwen3:1.7b")
OWNER_NAME = os.getenv("ARIA_OWNER_NAME", "Milad")
STATE_FILE = Path(os.getenv("ARIA_STATE_FILE", str(ROOT / "aria_state.json")))
MEMORY_DB = Path(os.getenv("ARIA_MEMORY_DB", str(ROOT / "aria_memory.db")))

LOCK = Lock()
MEMORY = MemoryStore(str(MEMORY_DB))
WEB_ROOT = ROOT / "web"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_pairing_code(code: str) -> str:
    """فقط رقم‌ها را نگه دار و فاصله/کاراکتر اضافه را حذف کن."""
    return "".join(ch for ch in str(code).strip() if ch.isdigit())


def load_state() -> dict:
    with LOCK:
        if not STATE_FILE.exists():
            return {}
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}


def save_state(state: dict) -> None:
    with LOCK:
        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def ensure_state() -> dict:
    state = load_state()
    if "pairing_code_hash" not in state:
        code = f"{secrets.randbelow(1_000_000):06d}"
        state = {
            "pairing_code_hash": sha256(code),
            "pairing_code_display": code,
            "created_at": int(time.time()),
            "owner_name": OWNER_NAME,
            "devices": [],
        }
        save_state(state)
    state.setdefault("owner_name", OWNER_NAME)
    state.setdefault("devices", [])
    return state


def regenerate_pairing_code() -> str:
    """کد جفت‌سازی جدید بساز و دستگاه‌های قبلی را نگه دار (فقط کد عوض شود)."""
    state = ensure_state()
    code = f"{secrets.randbelow(1_000_000):06d}"
    state["pairing_code_hash"] = sha256(code)
    state["pairing_code_display"] = code
    state["pairing_regenerated_at"] = int(time.time())
    save_state(state)
    return code


def ollama_available() -> bool:
    try:
        return requests.get(OLLAMA_TAGS_URL, timeout=3).ok
    except requests.RequestException:
        return False


def ask_local(prompt: str) -> tuple[str, dict]:
    decision = classify_request(prompt)
    memories = MEMORY.search(prompt, limit=5)
    recent = MEMORY.recent_conversation(limit=12)

    memory_text = "\n".join(
        f"- {item['content']}" for item in memories
    ) or "- مورد مرتبطی در حافظه پیدا نشد."

    recent_text = "\n".join(
        f"{item['role']}: {item['content']}" for item in recent
    )

    system = (
        f"تو ARIA هستی، دستیار شخصی {OWNER_NAME} و پروژه‌ای که او ساخته است. "
        "فارسی پاسخ بده مگر اینکه کاربر زبان دیگری بخواهد. "
        "برای کارهای حساس، مالی، مخرب یا تغییرات واقعی بدون تأیید مالک اقدام نکن. "
        "در این نسخه ابزار اجرایی فعال نیست. "
        "اگر اقدامی نیاز به مجوز دارد، واضح اعلام کن و ادعا نکن که انجام شده است.\n\n"
        f"سطح مجوز: {decision.level.value}\n"
        f"دلیل: {decision.reason}\n\n"
        f"حافظه مرتبط:\n{memory_text}\n\n"
        f"گفت‌وگوی اخیر:\n{recent_text}"
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()

    return response.json()["message"]["content"], {
        "level": decision.level.value,
        "requires_approval": decision.requires_approval,
        "reason": decision.reason,
    }


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ARIAHandler(BaseHTTPRequestHandler):
    server_version = "ARIA/0.4"

    def log_message(self, format: str, *args) -> None:
        print(f"[HTTP] {self.address_string()} - {format % args}")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def authorized(self) -> bool:
        token = self.headers.get("X-ARIA-Token", "")
        if not token:
            return False
        state = load_state()
        token_hash = sha256(token)
        return any(
            device.get("token_hash") == token_hash
            for device in state.get("devices", [])
        )

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            index_path = WEB_ROOT / "index.html"
            if index_path.exists():
                body = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            send_json(self, 500, {"error": "web_ui_missing"})
            return

        if self.path == "/status":
            state = load_state()
            send_json(
                self,
                200,
                {
                    "assistant": "ARIA",
                    "owner": state.get("owner_name", OWNER_NAME),
                    "model": MODEL,
                    "ollama": ollama_available(),
                    "internet": internet_available(),
                    "memory_items": len(MEMORY.search("", 100000)),
                    "paired_devices": len(state.get("devices", [])),
                    "server_time": int(time.time()),
                },
            )
            return

        if self.path == "/memory":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized", "message": "دستگاه احراز هویت نشده است."})
                return
            send_json(self, 200, {"memories": MEMORY.search("", 100)})
            return

        send_json(self, 404, {"error": "not_found", "message": "مسیر پیدا نشد."})

    def do_POST(self) -> None:
        if self.path == "/pair":
            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(
                    self,
                    400,
                    {
                        "error": "invalid_json",
                        "message": "بدنه درخواست JSON معتبر نیست.",
                    },
                )
                return

            state = ensure_state()
            raw_code = str(data.get("code", ""))
            code = normalize_pairing_code(raw_code)

            if len(code) != 6:
                send_json(
                    self,
                    400,
                    {
                        "error": "invalid_pairing_code",
                        "message": "کد جفت‌سازی باید دقیقاً ۶ رقم باشد. کد نمایش‌داده‌شده در ترمینال سرور را وارد کنید.",
                    },
                )
                return

            if sha256(code) != state.get("pairing_code_hash"):
                print(f"[PAIR] کد نامعتبر از {self.address_string()}: '{raw_code}' → نرمال‌شده: '{code}'")
                send_json(
                    self,
                    401,
                    {
                        "error": "invalid_pairing_code",
                        "message": "کد جفت‌سازی اشتباه است. همان کد ۶ رقمی که هنگام اجرای سرور در ترمینال چاپ شده را وارد کنید. اگر کد را گم کرده‌اید، سرور را یک‌بار با حذف aria_state.json ریستارت کنید تا کد جدید ساخته شود.",
                    },
                )
                return

            token = secrets.token_urlsafe(32)
            device_name = str(data.get("device_name", "Android")).strip()[:80] or "Android"
            state.setdefault("devices", []).append(
                {
                    "device_name": device_name,
                    "token_hash": sha256(token),
                    "paired_at": int(time.time()),
                }
            )
            save_state(state)

            print(f"[PAIR] دستگاه جدید جفت شد: {device_name}")
            send_json(
                self,
                200,
                {"assistant": "ARIA", "owner": OWNER_NAME, "token": token},
            )
            return

        if self.path == "/memory/add":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized", "message": "دستگاه احراز هویت نشده است."})
                return

            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(self, 400, {"error": "invalid_json", "message": "JSON نامعتبر است."})
                return

            content = str(data.get("content", "")).strip()
            kind = str(data.get("kind", "note")).strip()[:40] or "note"
            if not content:
                send_json(self, 400, {"error": "content_required", "message": "متن حافظه خالی است."})
                return

            memory_id = MEMORY.add_memory(content, kind=kind, source="owner")
            send_json(self, 200, {"saved": True, "memory_id": memory_id})
            return

        if self.path == "/chat":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized", "message": "دستگاه احراز هویت نشده است. ابتدا جفت‌سازی کنید."})
                return

            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(self, 400, {"error": "invalid_json", "message": "JSON نامعتبر است."})
                return

            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                send_json(self, 400, {"error": "prompt_required", "message": "پیام خالی است."})
                return

            if not ollama_available():
                send_json(
                    self,
                    503,
                    {
                        "error": "ollama_unavailable",
                        "message": "Ollama در دسترس نیست. سرویس Ollama را روی لپ‌تاپ اجرا کنید.",
                        "internet": internet_available(),
                    },
                )
                return

            try:
                answer, permission = ask_local(prompt)
            except requests.RequestException as exc:
                send_json(
                    self,
                    503,
                    {
                        "error": "ollama_request_failed",
                        "message": "ارتباط با مدل محلی ناموفق بود.",
                        "detail": str(exc),
                    },
                )
                return

            MEMORY.add_conversation("user", prompt)
            MEMORY.add_conversation("assistant", answer)

            send_json(
                self,
                200,
                {
                    "answer": answer,
                    "model": MODEL,
                    "permission": permission,
                    "offline_capable": True,
                },
            )
            return

        send_json(self, 404, {"error": "not_found", "message": "مسیر پیدا نشد."})


def local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
        sock.close()
        return address
    except OSError:
        return "127.0.0.1"


def main() -> None:
    state = ensure_state()
    print("=" * 56)
    print("ARIA | Local-first personal AI")
    print("=" * 56)
    print(f"Owner: {state.get('owner_name', OWNER_NAME)}")
    print(f"Model: {MODEL}")
    print(f"Server: http://{local_ip()}:{PORT}")
    print(f"Android pairing code: {state['pairing_code_display']}")
    print("  ↑ همین کد ۶ رقمی را در اپ اندروید وارد کن")
    print(f"Ollama: {'OK' if ollama_available() else 'NOT READY'}")
    print(f"Internet: {'ONLINE' if internet_available() else 'OFFLINE'}")
    print(f"Memory DB: {MEMORY_DB}")
    print(f"Paired devices: {len(state.get('devices', []))}")
    print("=" * 56)
    print("نکته: اگر کد را گم کردی، فایل aria_state.json را پاک کن و سرور را دوباره اجرا کن.")
    print("برای توقف سرور: Ctrl+C")

    server = ThreadingHTTPServer((HOST, PORT), ARIAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nARIA server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
