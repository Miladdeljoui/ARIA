"""Quota-protected Replicate clip generation for ARIA Telegram bot."""
import asyncio
import logging
import os
import tempfile
from pathlib import Path

import httpx

import billing

REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
MODEL_URL = "https://api.replicate.com/v1/models/minimax/video-01/predictions"
CLIP_SEMAPHORE = asyncio.Semaphore(1)
MAX_VIDEO_BYTES = 45 * 1024 * 1024
CHUNK_SIZE = 256 * 1024


async def create_prediction(prompt):
    if not REPLICATE_TOKEN:
        raise RuntimeError("REPLICATE_API_TOKEN تنظیم نشده است.")

    headers = {
        "Authorization": f"Bearer {REPLICATE_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait=1",
    }
    timeout = httpx.Timeout(connect=20, read=90, write=60, pool=20)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            MODEL_URL,
            headers=headers,
            json={"input": {"prompt": prompt[:2000], "prompt_optimizer": True}},
        )
        response.raise_for_status()
        prediction = response.json()

        get_url = (prediction.get("urls") or {}).get("get")
        if not get_url and prediction.get("id"):
            get_url = f"https://api.replicate.com/v1/predictions/{prediction['id']}"
        if not get_url:
            if prediction.get("status") == "succeeded":
                return prediction.get("output")
            raise RuntimeError("آدرس پیگیری ساخت کلیپ از سرویس دریافت نشد.")

        for _ in range(180):
            status = prediction.get("status")
            if status == "succeeded":
                return prediction.get("output")
            if status in ("failed", "canceled"):
                detail = prediction.get("error") or "ساخت کلیپ ناموفق بود."
                raise RuntimeError(str(detail)[:500])

            await asyncio.sleep(5)
            response = await client.get(get_url, headers=headers)
            response.raise_for_status()
            prediction = response.json()

        raise TimeoutError("زمان انتظار برای ساخت کلیپ به پایان رسید.")


async def download_video(url, destination):
    timeout = httpx.Timeout(connect=20, read=90, write=60, pool=20)
    total = 0
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            length = response.headers.get("content-length")
            if length and int(length) > MAX_VIDEO_BYTES:
                raise ValueError("حجم کلیپ از محدودیت مجاز بیشتر است.")
            with open(destination, "wb") as output:
                async for chunk in response.aiter_bytes(CHUNK_SIZE):
                    total += len(chunk)
                    if total > MAX_VIDEO_BYTES:
                        raise ValueError("حجم کلیپ از محدودیت مجاز بیشتر است.")
                    output.write(chunk)
    if total == 0:
        raise ValueError("فایل کلیپ خالی دریافت شد.")
    return total


def output_url(output):
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url") or first.get("video")
    if isinstance(output, dict):
        return output.get("url") or output.get("video")
    return None


async def generate_clip_for_user(update, context, prompt):
    message = update.effective_message
    user = update.effective_user
    prompt = (prompt or "").strip()
    if not message or not user or not prompt:
        return

    if len(prompt) > 2000:
        await message.reply_text("توضیح کلیپ حداکثر ۲۰۰۰ نویسه باشد.")
        return

    reservation = billing.reserve_clip(user.id)
    if not reservation["ok"]:
        reasons = {
            "no_active_subscription": "برای ساخت کلیپ ابتدا اشتراک کلیپ‌ساز تهیه کن.",
            "daily_quota_exhausted": "سهمیه روزانه این اشتراک تمام شده است.",
            "total_quota_exhausted": "سهمیه کلیپ این اشتراک به پایان رسیده است.",
        }
        await message.reply_text(
            reasons.get(reservation["reason"], "امکان رزرو سهمیه وجود ندارد."),
            reply_markup=None,
        )
        return

    job_id = reservation["job_id"]
    status_message = await message.reply_text(
        "🎬 درخواست ثبت شد. ساخت کلیپ ممکن است چند دقیقه زمان ببرد..."
    )
    file_path = None

    try:
        async with CLIP_SEMAPHORE:
            result = await create_prediction(prompt)
            url = output_url(result)
            if not url:
                raise RuntimeError("سرویس خروجی ویدئویی معتبری برنگرداند.")

            with tempfile.NamedTemporaryFile(
                prefix="aria_clip_", suffix=".mp4", delete=False
            ) as temp:
                file_path = temp.name

            await download_video(url, file_path)
            with open(file_path, "rb") as video:
                await message.reply_video(
                    video=video,
                    caption="🎬 کلیپ ساخته‌شده با ARIA AI",
                    read_timeout=180,
                    write_timeout=180,
                    connect_timeout=30,
                    pool_timeout=30,
                )

        billing.finish_clip(job_id, True)
        await status_message.edit_text(
            f"✅ کلیپ ارسال شد. سهمیه باقی‌مانده این اشتراک: {reservation['remaining']}"
        )
    except Exception as exc:
        logging.exception("Clip generation failed for user %s", user.id)
        billing.finish_clip(job_id, False)
        await status_message.edit_text(
            "❌ ساخت یا ارسال کلیپ ناموفق بود. سهمیه این درخواست به حسابت برگشت.\n"
            f"جزئیات: {str(exc)[:250]}"
        )
    finally:
        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
            except OSError:
                logging.warning("Temporary clip cleanup failed")
