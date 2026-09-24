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

from core.learning import extract_topic, research_topic, teaching_system_addon, wants_learning
from core.memory import MemoryStore
from core.permissions import classify_request
from core.runtime import internet_available
from core import self_learn
from core.tools import (
    iran_dev_mirrors_help,
    list_workspace,
    plan_android_build,
    run_safe_command,
    scaffold_android_screen,
    search_github_code,
    search_github_repos,
    write_project_file,
)

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
PENDING_APPROVALS: dict[str, dict] = {}

ARIA_PERSONA = (
    f"تو ARIA هستی؛ معلم و دستیار مهندسی {OWNER_NAME}. "
    "می‌توانی یاد بگیری، درس بدهی، در GitHub بگردی، طرح اپ اندروید بدهی و با تأیید مالک فایل در پروژه بنویسی. "
    "هرگز ادعا نکن بدون اجازه کل لپ‌تاپ را کنترل کردی. کارهای حساس را پیشنهاد کن و بگو نیاز به تأیید است. "
    "فارسی، دقیق، معلم‌گونه. هدف: توانمند کردن مالک برای ساخت و یادگیری، نه سلطه."
)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_pairing_code(code: str) -> str:
    # پشتیبانی از اعداد انگلیسی، فارسی و عربی که ممکن است از کیبورد موبایل ارسال شوند.
    digit_map = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    normalized = str(code).strip().translate(digit_map)
    return "".join(ch for ch in normalized if ch in "0123456789")


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
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


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
    state.setdefault("devices", [])
    return state


def ollama_diagnose() -> dict:
    result = {"ok": False, "tags_ok": False, "models": [], "hint": ""}
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=3)
        result["tags_ok"] = r.ok
        if r.ok:
            models = [m.get("name", "") for m in r.json().get("models", [])]
            result["models"] = models
            result["ok"] = any(MODEL in m or m.startswith(MODEL.split(":")[0]) for m in models)
            if not result["ok"]:
                result["hint"] = f"ollama pull {MODEL}"
        else:
            result["hint"] = "Ollama bad response"
    except requests.RequestException:
        result["hint"] = "ollama serve + ollama pull " + MODEL
    return result


def handle_special_commands(prompt: str) -> str | None:
    p = prompt.strip()
    low = p.casefold()

    if low.startswith("صف یادگیری:"):
        topics = [t.strip() for t in p.split(":", 1)[1].split(",") if t.strip()]
        for t in topics:
            self_learn.add_topic(t)
        return f"به صف یادگیری اضافه شد: {', '.join(topics)}"

    if low in ("خودآموزی روشن", "self learn on"):
        self_learn.enable(24)
        return "خودآموزی روزانه روشن شد. با «الان یاد بگیر» هم می‌توانی فوری اجرا کنی."

    if low in ("خودآموزی خاموش", "self learn off"):
        self_learn.disable()
        return "خودآموزی خاموش شد."

    if low in ("الان یاد بگیر", "learn now"):
        msg = self_learn.run_once(MEMORY)
        return msg or "صف یادگیری خالی است. اول بگو: صف یادگیری: موضوع۱, موضوع۲"

    if low.startswith("جستجو گیت‌هاب:") or low.startswith("جستجوی گیت‌هاب:"):
        q = p.split(":", 1)[1].strip()
        return search_github_code(q).message

    if low.startswith("ریپو گیت‌هاب:"):
        q = p.split(":", 1)[1].strip()
        return search_github_repos(q).message

    if low in ("راهنمای میرور ایران", "میرور ایران", "تحریم توسعه"):
        return iran_dev_mirrors_help().message

    if low.startswith("برنامه ساخت اپ:") or low.startswith("بساز اپ:"):
        idea = p.split(":", 1)[1].strip()
        return plan_android_build(idea).message

    if low.startswith("اسکلت اندروید:"):
        name = p.split(":", 1)[1].strip()
        # بدون تأیید فقط پیش‌نمایش
        result = scaffold_android_screen(name, approved=False)
        if result.needs_approval:
            aid = secrets.token_hex(4)
            PENDING_APPROVALS[aid] = {"type": "scaffold_android", "name": name}
            return (
                f"{result.message}\n\n"
                f"برای تأیید نوشتن فایل بگو: تأیید ابزار {aid}"
            )
        return result.message

    if low.startswith("تأیید ابزار "):
        aid = p.split("تأیید ابزار", 1)[1].strip()
        job = PENDING_APPROVALS.pop(aid, None)
        if not job:
            return "کد تأیید نامعتبر یا منقضی است."
        if job["type"] == "scaffold_android":
            return scaffold_android_screen(job["name"], approved=True).message
        return "نوع ابزار ناشناخته."

    if low.startswith("لیست پروژه"):
        return list_workspace().message

    return None


def ask_local(prompt: str) -> tuple[str, dict]:
    special = handle_special_commands(prompt)
    if special is not None:
        return special, {
            "level": "safe",
            "requires_approval": False,
            "reason": "special_command",
            "learning": False,
        }

    # خودآموزی پس‌زمینه اگر due باشد
    if self_learn.due():
        self_learn.run_once(MEMORY)

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
        meta["sources"] = packet.sources
        if not packet.blocked and packet.summary and not packet.offline:
            MEMORY.add_lesson(topic, packet.summary[:3000], " | ".join(packet.sources))

    memory_text = "\n".join(f"- {m['content'][:280]}" for m in memories) or "-"
    lesson_text = "\n".join(f"- {x['topic']}" for x in lessons) or "-"
    recent_text = "\n".join(f"{x['role']}: {x['content']}" for x in recent)

    system = (
        f"{ARIA_PERSONA}\n\n"
        f"مجوز: {decision.level.value} — {decision.reason}\n\n"
        f"حافظه:\n{memory_text}\n\nدرس‌ها:\n{lesson_text}\n\n"
        f"اخیر:\n{recent_text}\n\n{learning_block}\n"
        "دستورهای سیستمی که کاربر می‌تواند بگوید: "
        "صف یادگیری: ... | خودآموزی روشن | الان یاد بگیر | جستجو گیت‌هاب: ... | "
        "ریپو گیت‌هاب: ... | برنامه ساخت اپ: ... | اسکلت اندروید: ... | راهنمای میرور ایران"
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
    server_version = "ARIA/0.8-Agent"

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
            diag = ollama_diagnose()
            state = load_state()
            q = self_learn.load_queue()
            send_json(
                self,
                200,
                {
                    "assistant": "ARIA",
                    "owner": state.get("owner_name", OWNER_NAME),
                    "model": MODEL,
                    "ollama": diag["ok"] or diag["tags_ok"],
                    "internet": internet_available(),
                    "self_learn": q.get("enabled", False),
                    "learn_queue": q.get("topics", []),
                    "memory_items": len(MEMORY.search("", 100000)),
                    "paired_devices": len(state.get("devices", [])),
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
                {"memories": MEMORY.search("", 40), "lessons": MEMORY.search_lessons("", 40)},
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
                send_json(self, 401, {"error": "invalid_pairing_code"})
                return
            token = secrets.token_urlsafe(32)
            state.setdefault("devices", []).append(
                {
                    "device_name": str(data.get("device_name", "Device"))[:80],
                    "token_hash": sha256(token),
                    "paired_at": int(time.time()),
                }
            )
            save_state(state)
            send_json(self, 200, {"assistant": "ARIA", "owner": OWNER_NAME, "token": token})
            return

        if self.path == "/chat":
            if not self.authorized():
                send_json(self, 401, {"error": "unauthorized"})
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
            # دستورات ویژه حتی اگر مدل نباشد کار کنند
            special = handle_special_commands(prompt)
            if special is not None:
                MEMORY.add_conversation("user", prompt)
                MEMORY.add_conversation("assistant", special)
                send_json(self, 200, {"answer": special, "model": "aria-tools", "learning": False})
                return
            if not diag["ok"]:
                send_json(
                    self,
                    503,
                    {"error": "ollama_unavailable", "message": diag.get("hint", "")},
                )
                return
            try:
                answer, meta = ask_local(prompt)
            except requests.RequestException as e:
                send_json(self, 503, {"error": "ollama_request_failed", "message": str(e)})
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
    print("ARIA Agent | self-learn + safe tools")
    print("=" * 56)
    print(f"Server: http://{local_ip()}:{PORT}")
    print(f"Pairing: {state['pairing_code_display']}")
    print(f"Ollama: {'READY' if diag['ok'] else 'NEED ' + diag.get('hint','')}")
    print("Commands: صف یادگیری | خودآموزی روشن | جستجو گیت‌هاب | برنامه ساخت اپ")
    print("=" * 56)
    server = ThreadingHTTPServer((HOST, PORT), ARIAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
