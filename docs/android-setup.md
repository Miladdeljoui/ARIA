# ARIA Android + Laptop Setup

## Requirements

- Laptop with Python 3.10+ and Ollama
- Android Studio
- Android phone with Android 8.0 or newer
- Laptop and phone on the same Wi-Fi/LAN for this milestone

The current project uses AGP 9.4.0, Kotlin 2.2.10, compileSdk 37 and Compose BOM 2026.09.00.

## ایران: Mirror

For dependency/download problems caused by network restrictions, keep Liara Mirrors as an available fallback/reference:

https://liara.ir/mirrors/

A mirror does not guarantee that every dependency or service will be available. Use it only when the required artifact is legally and officially mirrored.

## Laptop

From the repository root:

```bash
cd server
pip install -r requirements.txt
python aria_server.py
```

The server prints a local URL and a **six-digit Android pairing code**.

Example:

```
Server: http://192.168.1.42:8765
Android pairing code: 482917
  ↑ همین کد ۶ رقمی را در اپ اندروید وارد کن
```

Do not publish `aria_state.json`. It is ignored by Git.

### اگر کد را گم کردی

1. سرور را متوقف کن (Ctrl+C)
2. فایل `aria_state.json` را حذف کن (در ریشه پروژه یا مسیر تنظیم‌شده)
3. دوباره `python aria_server.py` را اجرا کن → کد جدید ساخته می‌شود

## Android Studio

Open the `android` folder as an existing Android Studio project.

Use JDK 17 for the Gradle toolchain.

Build and install the app on the phone.

## Pairing (جفت‌سازی)

1. آدرس لپ‌تاپ را وارد کن (مثلاً `http://192.168.1.42:8765`)
2. **دقیقاً** همان کد ۶ رقمی که در ترمینال سرور چاپ شده را وارد کن
3. دکمه **اتصال** را بزن
4. اگر موفق شد پیام «لپ‌تاپ متصل شد ✓» را می‌بینی
5. یک پیام فارسی بفرست

### خطای `invalid_pairing_code`

این خطا یعنی کد واردشده با کد سرور یکی نیست. دلایل رایج:

- کد اشتباه تایپ شده (رقم کم/زیاد یا فاصله)
- سرور قبلاً ریستارت شده و کد جدید ساخته شده
- فایل `aria_state.json` پاک شده و کد عوض شده
- داری به سرور دیگری (Cloud یا لپ‌تاپ دیگر) وصل می‌شوی

راه‌حل: کد جدید را از ترمینال سرور کپی کن و دوباره اتصال بزن.

The server creates a device token for this phone. The phone stores the token locally.

## What works

- Laptop hosts the ARIA API.
- Android pairs as a trusted device.
- Android sends a prompt to the laptop.
- Laptop sends the prompt to local Qwen through Ollama.
- ARIA returns the response to Android.
- Android reads the response using Text-to-Speech.
- The server can report Ollama and internet status.

## Current limit

This first milestone needs a network path between phone and laptop. If the internet goes down while the phone and laptop remain on the same LAN, local chat can continue. If there is no path between the devices, Android cannot reach the laptop.

The next milestone adds permissions and structured memory.
