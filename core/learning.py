"""
لایه یادگیری و آموزش ARIA
- هر موضوعی که مالک بخواهد یاد بگیرد یا یاد بدهد
- منبع: حافظه محلی + در صورت آنلاین بودن، وب (ویکی‌پدیا فارسی/انگلیسی و منابع عمومی)
- بدون اجرای دستور مخرب؛ فقط دانش و توضیح
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import requests

from core.runtime import internet_available

# موضوعات حساس: فقط توضیح کلی، بدون دستور ساخت/سوءاستفاده
_BLOCK_HOWTO = re.compile(
    r"(ساخت\s*بمب|ساخت\s*اسلحه|چگونه\s*هاک|نفوذ\s*به\s*سیستم|"
    r"make\s*a\s*bomb|build\s*a\s*weapon|how\s*to\s*hack)",
    re.I,
)

_LEARN_HINTS = (
    "یاد بگیر",
    "یادبگیر",
    "به من یاد بده",
    "آموزش بده",
    "یاد بده",
    "توضیح بده",
    "چیست",
    "چیه",
    "یادگیری",
    "درس",
    "study",
    "teach",
    "learn",
    "explain",
    "what is",
)


@dataclass
class LearningPacket:
    topic: str
    summary: str
    sources: list[str]
    offline: bool
    blocked: bool = False


def wants_learning(text: str) -> bool:
    t = text.strip().casefold()
    return any(h in t for h in _LEARN_HINTS)


def extract_topic(text: str) -> str:
    t = text.strip()
    for prefix in (
        "به من یاد بده",
        "یاد بده",
        "آموزش بده",
        "یاد بگیر",
        "یادبگیر",
        "توضیح بده",
        "درباره",
        "teach me",
        "learn",
        "explain",
        "what is",
    ):
        if t.casefold().startswith(prefix):
            t = t[len(prefix) :].strip(" :،.-")
            break
    return t[:200] if t else text.strip()[:200]


def _clean_html(raw: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_wikipedia(topic: str, lang: str = "fa") -> Optional[tuple[str, str]]:
    """خلاصه ویکی‌پدیا. lang=fa برای ایران، en برای جهان."""
    api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(topic)}"
    try:
        r = requests.get(
            api,
            timeout=8,
            headers={"User-Agent": "ARIA-Learning/0.1 (personal educational assistant)"},
        )
        if r.status_code != 200:
            return None
        data = r.json()
        extract = (data.get("extract") or "").strip()
        url = data.get("content_urls", {}).get("desktop", {}).get("page") or data.get("url") or api
        if not extract:
            return None
        return extract[:2500], url
    except requests.RequestException:
        return None


def research_topic(topic: str) -> LearningPacket:
    if _BLOCK_HOWTO.search(topic):
        return LearningPacket(
            topic=topic,
            summary=(
                "این موضوع در محدودهٔ آموزش عملی خطرناک قرار می‌گیرد. "
                "ARIA فقط می‌تواند دربارهٔ مفاهیم کلی، تاریخچه یا جنبهٔ علمی غیرعملیاتی حرف بزند، "
                "نه دستور ساخت یا سوءاستفاده. موضوع را به شکل مفهومی بپرس."
            ),
            sources=[],
            offline=True,
            blocked=True,
        )

    if not internet_available():
        return LearningPacket(
            topic=topic,
            summary=(
                f"الان اینترنت در دسترس نیست. دربارهٔ «{topic}» از حافظه و دانش مدل محلی پاسخ می‌دهم. "
                "وقتی آنلاین شدی بگو «یاد بگیر: {topic}» تا از ویکی‌پدیا و منابع وب هم جمع کنم."
            ),
            sources=[],
            offline=True,
        )

    sources: list[str] = []
    parts: list[str] = []

    # اول فارسی (مناسب ایران)، بعد انگلیسی
    for lang in ("fa", "en"):
        hit = fetch_wikipedia(topic, lang=lang)
        if hit:
            extract, url = hit
            label = "ویکی‌پدیا فارسی" if lang == "fa" else "Wikipedia EN"
            parts.append(f"[{label}]\n{extract}")
            sources.append(url)

    if not parts:
        return LearningPacket(
            topic=topic,
            summary=(
                f"منبع وب آماده‌ای برای «{topic}» پیدا نشد. "
                "با دانش مدل محلی آموزش می‌دهم. می‌توانی موضوع را دقیق‌تر بنویسی."
            ),
            sources=[],
            offline=False,
        )

    summary = "\n\n".join(parts)[:4000]
    return LearningPacket(
        topic=topic,
        summary=summary,
        sources=sources,
        offline=False,
    )


def teaching_system_addon(packet: LearningPacket) -> str:
    src = "، ".join(packet.sources) if packet.sources else "فقط مدل محلی / حافظه"
    return (
        "حالت آموزش فعال است.\n"
        f"موضوع: {packet.topic}\n"
        f"منبع: {src}\n"
        "مواد خام تحقیق:\n"
        f"{packet.summary}\n\n"
        "وظیفه تو: مثل یک معلم صبور فارسی‌زبان، مرحله‌به‌مرحله و واضح آموزش بده. "
        "از ساده به پیشرفته برو. اگر مطلب برای مبتدی سخت است، اول مفهوم را بگو. "
        "در پایان ۲ سؤال تمرینی بپرس. منبع را ذکر کن. "
        "اگر مواد خام کافی نیست، صادقانه بگو و با دانش عمومی مدل ادامه بده."
    )
