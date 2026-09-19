"""
خودآموزی زمان‌بندی‌شده ARIA
هر روز/هر چند ساعت یک موضوع از صف یادگیری را از وب یا مدل محلی می‌خواند و در lessons ذخیره می‌کند.
کنترل لپ‌تاپ برای کارهای حساس جدا و با تأیید است.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from core.learning import research_topic
from core.memory import MemoryStore

QUEUE_FILE = Path(__file__).resolve().parents[1] / "aria_learn_queue.json"


def load_queue() -> dict:
    if not QUEUE_FILE.exists():
        return {"topics": [], "last_run": 0, "interval_hours": 24, "enabled": False}
    try:
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"topics": [], "last_run": 0, "interval_hours": 24, "enabled": False}


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_topic(topic: str) -> None:
    q = load_queue()
    topic = topic.strip()
    if topic and topic not in q["topics"]:
        q["topics"].append(topic)
    save_queue(q)


def enable(interval_hours: int = 24) -> None:
    q = load_queue()
    q["enabled"] = True
    q["interval_hours"] = max(1, interval_hours)
    save_queue(q)


def disable() -> None:
    q = load_queue()
    q["enabled"] = False
    save_queue(q)


def run_once(memory: MemoryStore) -> Optional[str]:
    q = load_queue()
    if not q.get("topics"):
        return None
    topic = q["topics"].pop(0)
    q["topics"].append(topic)  # چرخشی
    q["last_run"] = int(time.time())
    save_queue(q)

    packet = research_topic(topic)
    if packet.blocked:
        return f"رد شد (محدودیت ایمنی): {topic}"

    memory.add_lesson(
        topic=topic,
        content=packet.summary[:3000],
        sources=" | ".join(packet.sources),
    )
    memory.add_memory(
        content=f"[خودآموزی] {topic}\n{packet.summary[:1200]}",
        kind="self_learn",
        source="web" if packet.sources else "local",
    )
    return f"یاد گرفته شد: {topic} (منابع: {len(packet.sources)})"


def due(now: Optional[int] = None) -> bool:
    q = load_queue()
    if not q.get("enabled"):
        return False
    now = now or int(time.time())
    gap = int(q.get("interval_hours", 24)) * 3600
    return (now - int(q.get("last_run", 0))) >= gap
