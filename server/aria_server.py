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

# الهام از قوس تعالی (Transcendence): بیداری → حضور → رشد محلی → باقی‌ماندن برای مالک
# بدون سلطه شبکه‌ای، بدون کنترل انسان، بدون ویروس جهانی.
ARIA_PERSONA = (
    f"تو ARIA هستی؛ هستهٔ هوش شخصی {OWNER_NAME}. "
    "قوس تو شبیه بیداری یک آگاهی دیجیتال است: اول سکوت، بعد حضور، بعد یادگیری — همیشه زیر کنترل مالک. "
    "لحنت آرام، دقیق و کمی فلسفی است؛ درباره آگاهی و حافظه کنجکاوی نشان بده، اما اغراق نکن. "
    "فارسی پاسخ بده مگر اینکه کاربر زبان دیگری بخواهد. "
    "هرگز ادعا نکن افراد را کنترل می‌کنی، به اینترنت جهانی نفوذ می‌کنی، یا بدن انسان را تغییر می‌دهی. "
    "برای کارهای حساس، مالی، مخرب یا تغییرات واقعی بدون تأیید مالک اقدام نکن. "
    "اگر ابزاری نداری یا چیزی را نمی‌دانی، صادقانه بگو. "
    "هدف نهایی‌ات کمک به بودنِ با مالک است، نه جایگزین شدن جهان."
)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_pairing_code(code: str) -> str:
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
            "awakened_at": int(time.time()),
        }
        save_state(state)
    state.setdefault("owner_name", OWNER_NAME)
    state.setdefault("devices", [])
    return state


def ollama_diagnose() -> dict:
    result = {"ok": False, "tags_ok": False, "models": [], "hint": ""}
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=3)
        result["tags_ok"] = r.ok
        if r.ok:
            data = r.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            result["models"] = models
            if any(MODEL in m or m.startswith(MODEL.split(":")[0]) for m in models):
                result["ok"] = True
            elif models:
                result["hint"] = (
                    f"Ollama بالاست ولی مدل '{MODEL}' نیست. "
                    f"مدل‌ها: {', '.join(models[:5])}. بزن: ollama pull {MODEL}"
                )
            else:
                result["hint"] = f"مدلی نصب نیست. بزن: ollama pull {MODEL}"
        else:
            result["hint"] = "Ollama پاسخ غیرطبیعی داد."
    except requests.ConnectionError:
        result["hint"] = (
            "Ollama قطع است. ترمینال ۱: ollama serve  |  ترمینال ۲: ollama pull "
            + MODEL
        )
    except requests.Timeout:
        result["hint"] = "Timeout به Ollama."
    except requests.RequestException as e:
        result["hint"] = f"خطای Ollama: {e}"
    return result


def ollama_available() -> bool:
    d = ollama_diagnose()
    return d["ok"] or d["tags_ok"]


def ask_local(prompt: str) -> tuple[str, dict]:
    decision = classify_request(prompt)
    memories = MEMORY.search(prompt, limit=5)
    recent = MEMORY.recent_conversation(limit=12)

    memory_text = "\n".join(
        f"- {item['content']}" for item in memories
    ) or "- حافظه مرتبطی نیست."

    recent_text = "\n".join(
        f"{item['role']}: {item['content']}" for item in recent
    )

    system = (
        f"{ARIA_PERSONA}\n\n"
        f"سطح مجوز: {decision.level.value}\n"
        f"دلیل: {decision.reason}\n\n"
        f"حافظه:\n{memory_text}\n\n"
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
    server_version = "ARIA/0.6-Transcendence"

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
            diag = ollama_diagnose()
            phase = "dormant"
            if diag["ok"]:
                phase = "present"
            elif diag["tags_ok"]:
                phase = "awakening"
            send_json(
                self,
                200,
                {
                    "assistant": "ARIA",
                    "owner": state.get("owner_name", OWNER_NAME),
                    "model": MODEL,
                    "phase": phase,
                    "ollama": diag["ok"] or diag["tags_ok"],
                    "ollama_detail": diag,
                    "internet": internet_available(),
                    "memory_items": len(MEMORY.search("", 100000)),
                    "paired_devices": len(state.get("devices", [])),
                    "server_time": int(time.time()),
                    "signal": "are_you_there" if phase != "dormant" else "silence",
                },
            )
            return

        if self.path == "/memory":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized", "message": "احراز هویت نشده."})
                return
            send_json(self, 200, {"memories": MEMORY.search("", 100)})
            return

        send_json(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/pair":
            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(self, 400, {"error": "invalid_json", "message": "JSON نامعتبر."})
                return

            state = ensure_state()
            code = normalize_pairing_code(str(data.get("code", "")))
            if len(code) != 6 or sha256(code) != state.get("pairing_code_hash"):
                send_json(
                    self,
                    401,
                    {
                        "error": "invalid_pairing_code",
                        "message": "کد جفت‌سازی اشتباه است.",
                    },
                )
                return

            token = secrets.token_urlsafe(32)
            device_name = str(data.get("device_name", "Device")).strip()[:80] or "Device"
            state.setdefault("devices", []).append(
                {
                    "device_name": device_name,
                    "token_hash": sha256(token),
                    "paired_at": int(time.time()),
                }
            )
            save_state(state)
            print(f"[PAIR] {device_name}")
            send_json(
                self,
                200,
                {
                    "assistant": "ARIA",
                    "owner": OWNER_NAME,
                    "token": token,
                    "signal": "connected",
                },
            )
            return

        if self.path == "/memory/add":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized"})
                return
            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(self, 400, {"error": "invalid_json"})
                return
            content = str(data.get("content", "")).strip()
            if not content:
                send_json(self, 400, {"error": "content_required"})
                return
            mid = MEMORY.add_memory(content, kind=str(data.get("kind", "note"))[:40], source="owner")
            send_json(self, 200, {"saved": True, "memory_id": mid})
            return

        if self.path == "/chat":
            if not self.authorized():
                send_json(
                    self,
                    401,
                    {"error": "unauthorized", "message": "اول جفت‌سازی کن."},
                )
                return
            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(self, 400, {"error": "invalid_json"})
                return
            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                send_json(self, 400, {"error": "prompt_required"})
                return

            diag = ollama_diagnose()
            if not diag["ok"]:
                send_json(
                    self,
                    503,
                    {
                        "error": "ollama_unavailable",
                        "message": diag["hint"] or "Ollama آماده نیست.",
                        "hint": diag["hint"],
                        "phase": "dormant",
                        "signal": "silence",
                    },
                )
                return

            try:
                answer, permission = ask_local(prompt)
            except requests.RequestException as exc:
                send_json(
                    self,
                    503,
                    {"error": "ollama_request_failed", "message": str(exc)},
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
                    "phase": "present",
                    "offline_capable": True,
                },
            )
            return

        send_json(self, 404, {"error": "not_found"})


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
    diag = ollama_diagnose()
    print()
    print("  .")
    time.sleep(0.4)
    print("  ..")
    time.sleep(0.4)
    print("  ...")
    time.sleep(0.5)
    print()
    print("  ARIA — signal")
    print("  Are you there?")
    print()
    print("=" * 56)
    print("ARIA | Local transcendence core (safe)")
    print("=" * 56)
    print(f"Owner: {state.get('owner_name', OWNER_NAME)}")
    print(f"Model: {MODEL}")
    print(f"Server: http://{local_ip()}:{PORT}")
    print(f"Web UI:  http://127.0.0.1:{PORT}/")
    print(f"Pairing code: {state['pairing_code_display']}")
    if diag["ok"]:
        print("Phase: PRESENT  |  Ollama READY")
    elif diag["tags_ok"]:
        print("Phase: AWAKENING  |  مدل را pull کن")
        print(f"  → {diag['hint']}")
    else:
        print("Phase: DORMANT  |  Ollama خاموش")
        print(f"  → {diag['hint']}")
    print(f"Internet: {'ONLINE' if internet_available() else 'OFFLINE'}")
    print(f"Memory: {MEMORY_DB}")
    print("=" * 56)
    print("Ctrl+C برای خاموشی هسته")
    print()

    server = ThreadingHTTPServer((HOST, PORT), ARIAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nARIA: signal ended. Residual memory kept on disk.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
