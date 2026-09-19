from dataclasses import dataclass
from enum import Enum


class PermissionLevel(str, Enum):
    SAFE = "safe"
    APPROVAL = "approval"
    CRITICAL = "critical"


@dataclass(frozen=True)
class PermissionDecision:
    level: PermissionLevel
    requires_approval: bool
    reason: str


_CRITICAL_TERMS = (
    "پرداخت",
    "خرید",
    "رمز عبور",
    "پسورد",
    "حذف کامل",
    "فرمت",
    "factory reset",
    "factory-reset",
    "تغییر رمز",
    "انتقال پول",
)

_APPROVAL_TERMS = (
    "ارسال پیام",
    "ارسال ایمیل",
    "تماس بگیر",
    "تماس بگیر با",
    "اجرا کن",
    "run ",
    "اجرای ",
    "نصب ",
    "حذف فایل",
    "پاک کن",
    "تغییر تنظیمات",
    "دپلوی",
    "deploy",
    "انتشار",
    "آپلود",
    "دانلود فایل",
)


def classify_request(text: str) -> PermissionDecision:
    normalized = text.strip().casefold()

    if any(term.casefold() in normalized for term in _CRITICAL_TERMS):
        return PermissionDecision(
            level=PermissionLevel.CRITICAL,
            requires_approval=True,
            reason="این درخواست می‌تواند اثر مالی، امنیتی یا تخریبی جدی داشته باشد.",
        )

    if any(term.casefold() in normalized for term in _APPROVAL_TERMS):
        return PermissionDecision(
            level=PermissionLevel.APPROVAL,
            requires_approval=True,
            reason="این درخواست ممکن است تغییری واقعی در دستگاه، فایل یا ارتباط خارجی ایجاد کند.",
        )

    return PermissionDecision(
        level=PermissionLevel.SAFE,
        requires_approval=False,
        reason="درخواست فعلاً در محدوده گفت‌وگو و عملیات غیرتخریبی قرار می‌گیرد.",
    )
