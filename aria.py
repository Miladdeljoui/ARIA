import hashlib
import json
import os
import socket
import time
from pathlib import Path

import requests

OLLAMA_URL = os.getenv("ARIA_OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.getenv("ARIA_MODEL", "qwen3:1.7b")
STATE_FILE = Path("aria_state.json")


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def authenticate_owner() -> bool:
    state = load_state()

    if "owner_pin_hash" not in state:
        print("راه‌اندازی اولیه ARIA")
        print("یک PIN مالک برای اجرای ARIA تعیین کن.")
        pin = input("PIN جدید: ").strip()

        if len(pin) < 4:
            print("PIN باید حداقل ۴ رقم/کاراکتر داشته باشد.")
            return False

        state["owner_pin_hash"] = hash_pin(pin)
        state["created_at"] = int(time.time())
        state["memory"] = []
        save_state(state)
        print("PIN مالک ذخیره شد.")
        return True

    pin = input("PIN مالک: ").strip()
    return hash_pin(pin) == state["owner_pin_hash"]


def internet_available(timeout: float = 2.0) -> bool:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=timeout).close()
        return True
    except OSError:
        return False


def ollama_available() -> bool:
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        return response.ok
    except requests.RequestException:
        return False


def ask_local(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "تو ARIA هستی، دستیار شخصی مالک. "
                        "فارسی پاسخ بده مگر اینکه کاربر زبان دیگری بخواهد. "
                        "هیچ اقدام حساس یا خطرناکی را بدون تأیید مالک انجام نده. "
                        "در این مرحله فقط پاسخ متنی بده و ادعا نکن کاری انجام داده‌ای "
                        "مگر اینکه واقعاً ابزار آن را اجرا کرده باشی."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def show_status() -> None:
    state = load_state()
    print("\n--- وضعیت ARIA ---")
    print(f"Ollama: {'متصل' if ollama_available() else 'قطع'}")
    print(f"اینترنت: {'متصل' if internet_available() else 'قطع'}")
    print(f"مدل محلی: {MODEL}")
    print(f"حافظه ثبت‌شده: {len(state.get('memory', []))} مورد")
    print("------------------\n")


def remember(text: str) -> None:
    state = load_state()
    state.setdefault("memory", []).append(
        {"text": text, "created_at": int(time.time())}
    )
    save_state(state)


def main() -> None:
    if not authenticate_owner():
        print("احراز هویت مالک ناموفق بود.")
        return

    print("\nARIA آماده است. برای خروج /exit و برای وضعیت /status را بزن.\n")

    while True:
        prompt = input("تو: ").strip()

        if not prompt:
            continue
        if prompt == "/exit":
            print("ARIA خاموش شد.")
            break
        if prompt == "/status":
            show_status()
            continue
        if prompt.startswith("/remember "):
            remember(prompt[len("/remember "):].strip())
            print("ARIA: در حافظه محلی ثبت شد.")
            continue

        if not ollama_available():
            print("ARIA: Ollama در دسترس نیست. ابتدا Ollama را اجرا کن.")
            continue

        try:
            print("ARIA:", ask_local(prompt))
        except requests.RequestException as exc:
            print(f"ARIA: خطا در ارتباط با مدل محلی: {exc}")


if __name__ == "__main__":
    main()
