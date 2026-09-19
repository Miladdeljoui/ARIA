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


def ask_local(prompt: str, history: list[dict]) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                f"تو ARIA هستی، دستیار شخصی {OWNER_NAME} و پروژه‌ای که او ساخته است. "
                "با احترام و به زبان فارسی صحبت کن مگر اینکه کاربر زبان دیگری بخواهد. "
                "در مورد اقدامات واقعی، فقط کاری را ادعا کن که واقعاً توسط ابزار اجرا شده است. "
                "برای اقدامات حساس مانند حذف، تغییر تنظیمات امنیتی، ارسال پیام، پرداخت، "
                "انتشار کد یا دسترسی به داده حساس ابتدا تأیید مالک را بخواه. "
                "در این نسخه فقط گفت‌وگو و پاسخ متنی انجام می‌شود."
            ),
        }
    ]

    messages.extend(history[-12:])
    messages.append({"role": "user", "content": prompt})

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ARIAHandler(BaseHTTPRequestHandler):
    server_version = "ARIA/0.1"

    def log_message(self, format: str, *args) -> None:
        print(f"[HTTP] {self.address_string()} - {format % args}")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def authorized(self) -> bool:
        token = self.headers.get("X-ARIA-Token", "")
        state = load_state()
        return bool(token) and any(
            device.get("token_hash") == sha256(token)
            for device in state.get("devices", [])
        )

    def do_GET(self) -> None:
        if self.path == "/status":
            json_response(
                self,
                200,
                {
                    "assistant": "ARIA",
                    "owner": load_state().get("owner_name", OWNER_NAME),
                    "model": MODEL,
                    "ollama": ollama_available(),
                    "internet": internet_available(),
                    "server_time": int(time.time()),
                },
            )
            return

        json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/pair":
            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                json_response(self, 400, {"error": "invalid_json"})
                return

            code = str(data.get("code", "")).strip()
            state = ensure_state()

            if sha256(code) != state.get("pairing_code_hash"):
                json_response(self, 401, {"error": "invalid_pairing_code"})
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

            json_response(
                self,
                200,
                {
                    "assistant": "ARIA",
                    "owner": state.get("owner_name", OWNER_NAME),
                    "token": token,
                },
            )
            return

        if self.path == "/chat":
            if not self.authorized():
                json_response(self, 401, {"error": "unauthorized"})
                return

            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                json_response(self, 400, {"error": "invalid_json"})
                return

            prompt = str(data.get("prompt", "")).strip()
            history = data.get("history", [])

            if not prompt:
                json_response(self, 400, {"error": "prompt_required"})
                return

            if not isinstance(history, list):
                history = []

            try:
                answer = ask_local(prompt, history)
            except requests.RequestException as exc:
                json_response(
                    self,
                    503,
                    {"error": "ollama_unavailable", "detail": str(exc)},
                )
                return

            json_response(
                self,
                200,
                {
                    "answer": answer,
                    "model": MODEL,
                    "offline_capable": True,
                },
            )
            return

        json_response(self, 404, {"error": "not_found"})


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
    print(f"Ollama: {'OK' if ollama_available() else 'NOT READY'}")
    print(f"Internet: {'ONLINE' if internet_available() else 'OFFLINE'}")
    print("=" * 56)
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
