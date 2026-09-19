"""
ابزارهای ARIA برای لپ‌تاپ — فقط با تأیید مالک برای کارهای حساس.

اصل: پیشنهاد بده → مالک تأیید کند → اجرا.
هیچ‌وقت بدون تأیید: حذف سیستم، فرمت، ارسال پول، نصب پنهان، دسترسی خارج از workspace پروژه.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import requests

# ریشه امن: فقط داخل ریپوی ARIA یا مسیر صریح مجاز
REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOTS = [
    REPO_ROOT,
    REPO_ROOT / "android",
    REPO_ROOT / "generated",
]


@dataclass
class ToolResult:
    ok: bool
    name: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    needs_approval: bool = False


def _safe_path(path: str | Path) -> Optional[Path]:
    try:
        p = Path(path).expanduser().resolve()
    except OSError:
        return None
    for root in ALLOWED_ROOTS:
        try:
            p.relative_to(root.resolve())
            return p
        except ValueError:
            continue
    return None


def search_github_code(query: str, language: str = "", limit: int = 5) -> ToolResult:
    """جست‌وجو در GitHub برای کد/کتابخانه — مفید وقتی تحریم یا دانلود مستقیم سخت است."""
    q = query.strip()
    if language:
        q = f"{q} language:{language}"
    url = f"https://api.github.com/search/code?q={quote(q)}&per_page={min(limit, 10)}"
    try:
        r = requests.get(
            url,
            timeout=12,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ARIA-Local-Assistant",
            },
        )
        if r.status_code == 403:
            return ToolResult(
                False,
                "github_search",
                "GitHub API محدودیت نرخ یا نیاز به توکن دارد. بعداً دوباره امتحان کن یا GITHUB_TOKEN بگذار.",
            )
        if not r.ok:
            return ToolResult(False, "github_search", f"GitHub status {r.status_code}")
        items = r.json().get("items", [])[:limit]
        lines = []
        for it in items:
            repo = it.get("repository", {}).get("full_name", "")
            path = it.get("path", "")
            html = it.get("html_url", "")
            lines.append(f"- {repo}/{path}\n  {html}")
        text = "\n".join(lines) if lines else "نتیجه‌ای پیدا نشد."
        return ToolResult(True, "github_search", text, {"count": len(items), "items": items})
    except requests.RequestException as e:
        return ToolResult(False, "github_search", f"خطای شبکه: {e}")


def search_github_repos(query: str, limit: int = 5) -> ToolResult:
    url = f"https://api.github.com/search/repositories?q={quote(query)}&per_page={min(limit, 10)}"
    try:
        r = requests.get(
            url,
            timeout=12,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ARIA-Local-Assistant",
            },
        )
        if not r.ok:
            return ToolResult(False, "github_repos", f"GitHub status {r.status_code}")
        items = r.json().get("items", [])[:limit]
        lines = []
        for it in items:
            lines.append(
                f"- {it.get('full_name')} ★{it.get('stargazers_count', 0)}\n"
                f"  {it.get('description') or ''}\n  {it.get('html_url')}"
            )
        return ToolResult(
            True,
            "github_repos",
            "\n".join(lines) if lines else "ریپویی پیدا نشد.",
            {"count": len(items)},
        )
    except requests.RequestException as e:
        return ToolResult(False, "github_repos", str(e))


def iran_dev_mirrors_help() -> ToolResult:
    """راهنمای مسیرهای رایج توسعه زیر محدودیت شبکه ایران (عمومی و قانونی)."""
    text = (
        "مسیرهای پیشنهادی توسعه در ایران (عمومی):\n"
        "1) Liara Mirrors: https://liara.ir/mirrors/\n"
        "2) وابستگی‌ها را از GitHub clone کن وقتی مستقیم Gradle/Maven قطع است.\n"
        "3) در android/gradle.properties می‌توانی mirror رسمی سازمان را تنظیم کنی اگر موجود باشد.\n"
        "4) برای npm: registryهای داخلی معتبر سازمان‌ها (در صورت استفاده).\n"
        "5) Ollama مدل را یک‌بار دانلود کن و آفلاین کار کن.\n"
        "ARIA فقط راهنمایی می‌کند؛ تو تأیید و اجرا می‌کنی."
    )
    return ToolResult(True, "iran_mirrors", text)


def write_project_file(rel_path: str, content: str, approved: bool = False) -> ToolResult:
    if not approved:
        return ToolResult(
            False,
            "write_file",
            f"نیاز به تأیید مالک برای نوشتن: {rel_path}",
            {"path": rel_path, "preview": content[:500]},
            needs_approval=True,
        )
    target = _safe_path(REPO_ROOT / rel_path)
    if target is None:
        return ToolResult(False, "write_file", "مسیر خارج از فضای مجاز پروژه است.")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(True, "write_file", f"نوشته شد: {target}", {"path": str(target)})
    except OSError as e:
        return ToolResult(False, "write_file", str(e))


def scaffold_android_screen(
    feature_name: str,
    package: str = "com.miladdeljoui.aria",
    approved: bool = False,
) -> ToolResult:
    """اسکلت یک صفحه Compose ساده داخل generated/ — نه اجرای مستقیم Android Studio."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "", feature_name) or "Feature"
    class_name = safe[0].upper() + safe[1:] if safe else "Feature"
    rel = f"generated/android/{class_name}Screen.kt"
    code = f'''package {package}

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * تولیدشده توسط ARIA — بازبینی و انتقال به ماژول android/app توسط مالک.
 * Feature: {feature_name}
 */
@Composable
fun {class_name}Screen() {{
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {{
        Text("{feature_name}")
        Text("این صفحه را در Android Studio باز کن، بررسی کن، بعد به پروژه اصلی منتقل کن.")
    }}
}}
'''
    return write_project_file(rel, code, approved=approved)


def list_workspace(sub: str = "") -> ToolResult:
    base = _safe_path(REPO_ROOT / sub) if sub else REPO_ROOT.resolve()
    if base is None or not base.exists():
        return ToolResult(False, "list_workspace", "مسیر نامعتبر")
    entries = []
    try:
        for p in sorted(base.iterdir())[:80]:
            entries.append(("DIR " if p.is_dir() else "FILE") + f" {p.name}")
        return ToolResult(True, "list_workspace", "\n".join(entries), {"path": str(base)})
    except OSError as e:
        return ToolResult(False, "list_workspace", str(e))


def run_safe_command(command: str, approved: bool = False) -> ToolResult:
    """فقط چند دستور سفیدلیست؛ نیاز به تأیید."""
    allowed_prefixes = (
        "git status",
        "git log",
        "git pull",
        "git diff",
        "ollama list",
        "dir",
        "ls",
        "python --version",
    )
    cmd = command.strip()
    if not any(cmd.startswith(p) for p in allowed_prefixes):
        return ToolResult(
            False,
            "run_command",
            "این دستور در لیست سفید نیست. برای امنیت فقط دستورات محدود مجازند.",
            needs_approval=False,
        )
    if not approved:
        return ToolResult(
            False,
            "run_command",
            f"نیاز به تأیید برای اجرا: {cmd}",
            {"command": cmd},
            needs_approval=True,
        )
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return ToolResult(proc.returncode == 0, "run_command", out[:4000] or "(بدون خروجی)")
    except Exception as e:
        return ToolResult(False, "run_command", str(e))


def plan_android_build(app_idea: str) -> ToolResult:
    """برنامه ساخت اپ — اجرا در Studio با دست مالک."""
    plan = (
        f"طرح ساخت اپ برای: {app_idea}\n\n"
        "1) در Android Studio پروژه ARIA/android را باز کن.\n"
        "2) یک Composable/Activity جدید برای این قابلیت بساز.\n"
        "3) از ARIA بخواه اسکلت کد را با تأیید تولید کند (scaffold).\n"
        "4) وابستگی‌ها: اگر دانلود قطع بود از GitHub/mirror استفاده کن.\n"
        "5) Build > Make Project و روی گوشی تست کن.\n\n"
        "ARIA کد را پیشنهاد و در پوشه generated می‌نویسد؛ "
        "اجرای کامل Android Studio را خودت با تأیید انجام بده."
    )
    return ToolResult(True, "android_plan", plan)
