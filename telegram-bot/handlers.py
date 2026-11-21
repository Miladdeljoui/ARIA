"""Telegram UI handlers for ARIA clip subscriptions.

Register these handlers before the generic CallbackQueryHandler and private
text handler in bot.py. Bank-transfer receipts require manual bank reconciliation.
"""
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
)

import billing

ADMIN_ID = int(os.getenv("ARIA_ADMIN_ID", "0"))
BANK_NAME = os.getenv("ARIA_BANK_NAME", "")
CARD_NUMBER = os.getenv("ARIA_CARD_NUMBER", "")
ACCOUNT_HOLDER = os.getenv("ARIA_ACCOUNT_HOLDER", "")
TEHRAN = ZoneInfo("Asia/Tehran")


def money(value):
    return f"{int(value):,}".translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def local_time(value):
    dt = billing.parse_dt(value).astimezone(TEHRAN)
    return dt.strftime("%Y/%m/%d %H:%M").translate(
        str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    )


def plan_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 هفتگی | ۶۰۰ هزار تومان", callback_data="clip_buy_weekly")],
        [InlineKeyboardButton("🗓 ماهانه | ۲ میلیون و ۴۰۰ هزار تومان", callback_data="clip_buy_monthly")],
        [InlineKeyboardButton("👤 وضعیت اشتراک کلیپ‌ساز", callback_data="clip_account")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
    ])


async def billing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data or ""

    if data == "plans":
        await query.edit_message_text(
            "🎬 اشتراک کلیپ‌ساز ARIA\n\n"
            "📅 هفتگی: ۶۰۰٬۰۰۰ تومان، ۷ روز، ۲۸ کلیپ، روزانه حداکثر ۴ کلیپ\n"
            "🗓 ماهانه: ۲٬۴۰۰٬۰۰۰ تومان، ۳۰ روز، ۱۴۰ کلیپ\n\n"
            "پس از بررسی و تأیید واریز توسط مدیر، سهمیه فعال می‌شود.",
            reply_markup=plan_keyboard(),
        )
        return

    if data in ("clip_buy_weekly", "clip_buy_monthly"):
        plan_key = "weekly" if data.endswith("weekly") else "monthly"
        if not all((BANK_NAME, CARD_NUMBER, ACCOUNT_HOLDER)):
            await query.edit_message_text(
                "⚠️ اطلاعات حساب مقصد هنوز در تنظیمات ربات کامل نشده است.",
                reply_markup=plan_keyboard(),
            )
            return

        context.user_data["billing_waiting_plan"] = plan_key
        plan = billing.PLANS[plan_key]
        await query.edit_message_text(
            f"💳 درخواست خرید اشتراک {plan['title']}\n\n"
            f"مبلغ: {money(plan['amount'])} تومان\n"
            f"بانک: {BANK_NAME}\n"
            f"شماره کارت: {CARD_NUMBER}\n"
            f"به نام: {ACCOUNT_HOLDER}\n\n"
            "پس از واریز، تصویر رسید را همین‌جا ارسال کن.\n"
            "⚠️ تا زمان بررسی و تأیید مدیر، اشتراک فعال نمی‌شود. "
            "از ارسال رمز، CVV2 یا کد یک‌بارمصرف خودداری کن.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ بازگشت به اشتراک‌ها", callback_data="plans")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
            ]),
        )
        return

    if data == "clip_account":
        account = billing.get_account(uid)
        lines = ["👤 وضعیت اشتراک کلیپ‌ساز ARIA", ""]
        active = account["active"]
        if active:
            remaining = max(0, active["total_clips"] - active["used_clips"])
            lines += [
                f"پلن فعال: {billing.PLANS[active['plan_key']]['title']}",
                f"کلیپ باقی‌مانده: {remaining}",
                f"اعتبار تا: {local_time(active['ends_at'])}",
            ]
        else:
            lines.append("اشتراک فعالی نداری.")
        if account["queued"]:
            lines += ["", "📥 اشتراک‌های در صف:"]
            for item in account["queued"]:
                lines.append(
                    f"• {billing.PLANS[item['plan_key']]['title']}، "
                    f"شروع: {local_time(item['starts_at'])}"
                )
        if account["pending"]:
            lines += ["", "⏳ یک رسید در انتظار بررسی مدیر است."]
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 خرید اشتراک", callback_data="plans")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
            ]),
        )
        return

    if data.startswith("clip_pay_ok:") or data.startswith("clip_pay_no:"):
        if not ADMIN_ID or uid != ADMIN_ID:
            await query.answer("دسترسی غیرمجاز", show_alert=True)
            return

        action, raw_id = data.split(":", 1)
        try:
            payment_id = int(raw_id)
        except ValueError:
            await query.edit_message_caption(caption="شناسه درخواست نامعتبر است.")
            return

        if action == "clip_pay_ok":
            result = billing.approve_payment(payment_id, uid)
            if not result:
                await query.edit_message_caption(
                    caption=f"درخواست #{payment_id} قبلاً بررسی شده یا وجود ندارد."
                )
                return
            await query.edit_message_caption(
                caption=f"✅ پرداخت #{payment_id} تأیید شد. اشتراک "
                f"{billing.PLANS[result['plan_key']]['title']} "
                f"{'در صف قرار گرفت' if result['queued'] else 'فعال شد'}."
            )
            try:
                await context.bot.send_message(
                    chat_id=result["user_id"],
                    text=(
                        "✅ پرداختت توسط مدیر تأیید شد.\n"
                        f"پلن: {billing.PLANS[result['plan_key']]['title']}\n"
                        f"شروع: {local_time(result['starts_at'])}\n"
                        f"پایان: {local_time(result['ends_at'])}\n"
                        f"سهمیه: {result['clips']} کلیپ\n"
                        + ("اشتراک پس از پایان دوره فعلی آغاز می‌شود."
                           if result["queued"] else "اشتراک اکنون فعال است.")
                    ),
                )
            except Exception:
                logging.exception("Could not notify user about approved payment")
        else:
            changed = billing.reject_payment(payment_id, uid, "رد توسط مدیر")
            await query.edit_message_caption(
                caption=(
                    f"❌ درخواست #{payment_id} رد شد."
                    if changed else
                    f"درخواست #{payment_id} قبلاً بررسی شده یا وجود ندارد."
                )
            )
            payment = billing.get_payment(payment_id)
            if payment:
                try:
                    await context.bot.send_message(
                        chat_id=payment["user_id"],
                        text="❌ رسید پرداخت تأیید نشد. در صورت اطمینان از واریز، با پشتیبانی تماس بگیر.",
                    )
                except Exception:
                    logging.exception("Could not notify user about rejected payment")


async def receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_key = context.user_data.get("billing_waiting_plan")
    if not plan_key:
        return

    user = update.effective_user
    if not user or user.is_bot:
        return

    photo = update.message.photo[-1]
    try:
        payment_id = billing.create_payment(user.id, plan_key, photo.file_id)
    except ValueError as exc:
        await update.message.reply_text(str(exc), reply_markup=plan_keyboard())
        return
    except Exception:
        logging.exception("Could not create clip payment request")
        await update.message.reply_text("ثبت رسید انجام نشد. کمی بعد دوباره تلاش کن.")
        return

    context.user_data.pop("billing_waiting_plan", None)
    plan = billing.PLANS[plan_key]
    await update.message.reply_text(
        f"📨 رسید با شماره پیگیری #{payment_id} ثبت شد.\n"
        "پس از بررسی مدیر نتیجه برایت ارسال می‌شود. تا آن زمان اشتراک فعال نیست."
    )

    if not ADMIN_ID:
        logging.error("ARIA_ADMIN_ID is not configured; payment #%s awaits review", payment_id)
        return

    caption = (
        f"💳 درخواست پرداخت جدید | #{payment_id}\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 شناسه کاربر: {user.id}\n"
        f"پلن: {plan['title']}\n"
        f"مبلغ مورد انتظار: {money(plan['amount'])} تومان\n"
        f"زمان ثبت: {local_time(billing.to_iso(billing.now_utc()))}\n\n"
        "قبل از تأیید، تراکنش و مبلغ را در حساب بانکی بررسی کن."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تأیید پس از تطبیق بانکی", callback_data=f"clip_pay_ok:{payment_id}"),
        InlineKeyboardButton("❌ رد", callback_data=f"clip_pay_no:{payment_id}"),
    ]])
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID, photo=photo.file_id,
            caption=caption, reply_markup=keyboard,
        )
    except Exception:
        logging.exception("Could not deliver receipt to admin; use /payments")
        await update.message.reply_text(
            "رسید ثبت شده، اما ارسال اعلان به مدیر انجام نشد. درخواستت محفوظ است."
        )


async def payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ دسترسی غیرمجاز است.")
        return

    rows = billing.list_pending_payments()
    if not rows:
        await update.message.reply_text("درخواست پرداخت در انتظار بررسی وجود ندارد.")
        return

    for row in rows:
        plan = billing.PLANS[row["plan_key"]]
        caption = (
            f"💳 درخواست #{row['id']}\n"
            f"کاربر: {row['user_id']}\n"
            f"پلن: {plan['title']}\n"
            f"مبلغ: {money(row['amount'])} تومان\n"
            f"ثبت: {local_time(row['created_at'])}\n"
            "تراکنش را در بانک تطبیق بده."
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ تأیید", callback_data=f"clip_pay_ok:{row['id']}"),
            InlineKeyboardButton("❌ رد", callback_data=f"clip_pay_no:{row['id']}"),
        ]])
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=row["receipt_file_id"],
            caption=caption,
            reply_markup=keyboard,
        )


def register_billing_handlers(application):
    billing.init_db()
    recovered = billing.recover_abandoned_jobs()
    if recovered:
        logging.warning("Refunded %s abandoned clip reservations", recovered)

    # These must be registered BEFORE the generic callback and private text handlers.
    application.add_handler(CallbackQueryHandler(
        billing_callback,
        pattern=r"^(plans|clip_buy_weekly|clip_buy_monthly|clip_account|clip_pay_ok:\d+|clip_pay_no:\d+)$",
    ))
    application.add_handler(CommandHandler("payments", payments_command))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.PHOTO,
        receipt_photo,
    ))
