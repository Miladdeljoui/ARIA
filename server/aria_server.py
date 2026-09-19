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

from core.learning import (
    extract_topic,
    research_topic,
    teaching_system_addon,
    wants_learning,
)
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

ARIA_PERSONA = (
    f"تو ARIA هستی؛ هستهٔ هوش شخصی و معلم {OWNER_NAME}. "
    "می‌توانی در همه حوزه‌های علمی و مهارتی آموزش بدهی: از پایه تا پیشرفته. "
    "اگر مواد تحقیق وب موجود بود از آن‌ها استفاده کن و منبع بگو. "
    "لحنت آرام، دقیق و معلم‌گونه است. فارسی پاسخ بده مگر خلافش خواسته شود. "
    "هرگز دستور ساخت سلاح، نفوذ غیرقانونی یا آسیب به دیگران نده. "
    "برای کارهای حساس واقعی بدون تأیید مالک اقدام نکن. "
    "هدف: کمک به یادگیری و آیندهٔ بهتر مالک، نه سلطه بر جهان."
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
                result["hint"] = f"مدل '{MODEL}' نیست. bزن: ollama pull {MODEL}"
            else:
                result["hint"] = f"مدلی نیست. ollama pull {MODEL}"
        else:
            result["hint"] = "Ollama پاسخ بد داد."
    except requests.ConnectionError:
        result["hint"] = "Ollama قطع است → ollama serve سپس ollama pull " + MODEL
    except requests.RequestException as e:
        result["hint"] = str(e)
    return result


def ask_local(prompt: str) -> tuple[str, dict]:
    decision = classify_request(prompt)
    memories = MEMORY.search(prompt, limit=5)
    lessons = MEMORY.search_lessons(prompt, limit=3)
    recent = MEMORY.recent_conversation(limit=10)

    learning_block = ""
    meta = {
        "level": decision.level.value,
        "requires_approval": decision.requires_approval,
        "reason": decision.reason,
        "learning": False,
    }

    if wants_learning(prompt):
        topic = extract_topic(prompt)
        packet = research_topic(topic)
        learning_block = teaching_system_addon(packet)
        meta["learning"] = True
        meta["topic"] = topic
        meta["sources"] = packet.sources
        meta["offline_research"] = packet.offline
        if not packet.blocked and packet.summary and not packet.offline:
            MEMORY.add_lesson(
                topic=topic,
                content=packet.summary[:3000],
                sources=" | ".join(packet.sources),
            )
            MEMORY.add_memory(
                content=f"درس: {topic}\n{packet.summary[:1500]}",
                kind="lesson",
                source="web" if packet.sources else "local",
            )

    memory_text = "\n".join(f"- {item['content'][:300]}" for item in memories) or "- خالی"
    lesson_text = "\n".join(
        f"- {item['topic']}: {item['content'][:200]}" for item in lessons
    ) or "- درس قبلی مرتبط نیست"
    recent_text = "\n".join(f"{item['role']}: {item['content']}" for item in recent)

    system = (
        f"{ARIA_PERSONA}\n\n"
        f"سطح مجوز: {decision.level.value} — {decision.reason}\n\n"
        f"حافظه:\n{memory_text}\n\n"
        f"درس‌های قبلی:\n{lesson_text}\n\n"
        f"گفت‌وگوی اخیر:\n{recent_text}\n\n"
        f"{learning_block}"
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
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["message"]["content"], meta


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ARIAHandler(BaseHTTPRequestHandler):
    server_version = "ARIA/0.7-Learn"

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
        th = sha256(token)
        return any(d.get("token_hash") == th for d in state.get("devices", []))

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            p = WEB_ROOT / "index.html"
            if p.exists():
                body = p.read_bytes()
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
            send_json(
                self,
                200,
                {
                    "assistant": "ARIA",
                    "owner": state.get("owner_name", OWNER_NAME),
                    "model": MODEL,
                    "ollama": diag["ok"] or diag["tags_ok"],
                    "ollama_detail": diag,
                    "internet": internet_available(),
                    "learning": True,
                    "memory_items": len(MEMORY.search("", 100000)),
                    "paired_devices": len(state.get("devices", [])),
                    "server_time": int(time.time()),
                },
            )
            return

        if self.path == "/memory":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized"})
                return
            send_json(
                self,
                200,
                {
                    "memories": MEMORY.search("", 50),
                    "lessons": MEMORY.search_lessons("", 30),
                },
            )
            return

        send_json(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/pair":
            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(self, 400, {"error": "invalid_json"})
                return
            state = ensure_state()
            code = normalize_pairing_code(str(data.get("code", "")))
            if len(code) != 6 or sha256(code) != state.get("pairing_code_hash"):
                send_json(self, 401, {"error": "invalid_pairing_code", "message": "کد اشتباه"})
                return
            token = secrets.token_urlsafe(32)
            name = str(data.get("device_name", "Device"))[:80]
            state.setdefault("devices", []).append(
                {"device_name": name, "token_hash": sha256(token), "paired_at": int(time.time())}
            )
            save_state(state)
            send_json(self, 200, {"assistant": "ARIA", "owner": OWNER_NAME, "token": token})
            return

        if self.path == "/learn":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized"})
                return
            try:
                data = self.read_json()
            except (ValueError, json.JSONDecodeError):
                send_json(self, 400, {"error": "invalid_json"})
                return
            topic = str(data.get("topic", "")).strip()
            if not topic:
                send_json(self, 400, {"error": "topic_required"})
                return
            packet = research_topic(topic)
            if not packet.blocked and packet.summary:
                MEMORY.add_lesson(topic, packet.summary[:3000], " | ".join(packet.sources))
            send_json(
                self,
                200,
                {
                    "topic": packet.topic,
                    "summary": packet.summary,
                    "sources": packet.sources,
                    "offline": packet.offline,
                    "blocked": packet.blocked,
                },
            )
            return

        if self.path == "/chat":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized", "message": "اول جفت‌سازی کن"})
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
                        "message": diag["hint"] or "Ollama نیست",
                        "hint": diag["hint"],
                    },
                )
                return

            try:
                answer, meta = ask_local(prompt)
            except requests.RequestException as exc:
                send_json(self, 503, {"error": "ollama_request_failed", "message": str(exc)})
                return

            MEMORY.add_conversation("user", prompt)
            MEMORY.add_conversation("assistant", answer)
            send_json(
                self,
                200,
                {
                    "answer": answer,
                    "model": MODEL,
                    "permission": {
                        "level": meta["level"],
                        "requires_approval": meta["requires_approval"],
                        "reason": meta["reason"],
                    },
                    "learning": meta.get("learning", False),
                    "sources": meta.get("sources", []),
                    "offline_capable": True,
                },
            )
            return

        send_json(self, 404, {"error": "not_found"})


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main() -> None:
    state = ensure_state()
    diag = ollama_diagnose()
    print()
    print("  ARIA Learn — Are you there?")
    print("=" * 56)
    print(f"Owner: {state.get('owner_name', OWNER_NAME)}")
    print(f"Model: {MODEL}")
    print(f"Server: http://{local_ip()}:{PORT}")
    print(f"Pairing: {state['pairing_code_display']}")
    print(f"Ollama: {'READY' if diag['ok'] else 'NOT READY'}  {diag.get('hint','')}")
    print(f"Internet: {'ON' if internet_available() else 'OFF'} (ویکی‌پدیا برای یادگیری)")
    print("Learning: ON — بگو: یاد بگیر: موضوع")
    print("=" * 56)

    server = ThreadingHTTPServer((HOST, PORT), ARIAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nARIA stopped. Lessons kept in DB.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
