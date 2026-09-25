# Learning 09: Jev ecosystem research

تاریخ ثبت: 2026-09-25

## ایده
این یادداشت مجموعه پروژه‌هایی را که کاربر معرفی کرده ثبت می‌کند. نکته مهم: نام «Jev» و آمار ستاره‌های ذکرشده در متن ارسالی کاربر در این مرحله مستقل از منبع اصلی راستی‌آزمایی نشده‌اند، بنابراین این اعداد به‌عنوان واقعیت قطعی پروژه ثبت نمی‌شوند.

## پروژه‌های معرفی‌شده
- jev-trader — ربات معاملاتی برای Monad با سفارش‌های limit و تصمیم‌گیری توسط Jev.
  - https://github.com/jarrodwatts/jev-trader
- jev-ultrafast — عامل مرورگر با انتخاب کلیک و فراخوانی مدل متنی فقط در نقاط لازم.
  - https://github.com/browser-use/jev-ultrafast
- jev-doom-agent — Chocolate Doom کامپایل‌شده به WebAssembly با تصمیم‌گیری تاکتیکی.
  - https://github.com/lukaske/jev-doom-agent
- jev-t-rex-runner — بازی Chrome Dino با تصمیم‌گیری عامل برای پرش/خم‌شدن/ادامه.
  - https://github.com/joshlarsen/jev-t-rex-runner
- typesafe-chess — مقایسه Jev با موتور جست‌وجوی شطرنج.
  - https://github.com/TholeG/typesafe-chess
- jev-drone — شبیه‌ساز کوادکوپتر با دوربین و تصمیم‌گیری دوره‌ای برای عبور از موانع.
  - https://github.com/RomanSlack/jev-drone
- tax-doc-classifier — دسته‌بندی فرم‌های مالیاتی IRS.
  - https://github.com/kyotofin/tax-doc-classifier
- killmyidea — ارزیابی ساختاری ایده استارتاپ و خروجی kill/fix/ship.
  - https://github.com/monteduro/killmyidea
- jev-curate — پردازش Parquet/JSONL با قضاوت‌های typed و فیلتر کردن رکوردها.
  - https://github.com/AkashPriyadarshii/jev-curate
- pg-jev — افزونه PostgreSQL برای پرسش طبیعی از جدول‌ها.
  - https://github.com/realZachi/pg-jev

## چیزهایی که برای ARIA ارزش بررسی دارند
1. Agentic control loop: تصمیم‌گیری تکرارشونده، مشاهده وضعیت، انتخاب عمل، دریافت نتیجه.
2. Fast action / slow reasoning: انجام بعضی تصمیم‌های ساده بدون فراخوانی مداوم مدل بزرگ.
3. Browser automation: جدا کردن مشاهده صفحه، انتخاب action و اجرای action با Permission Engine.
4. Game/simulation environments: استفاده از محیط‌های امن برای تست عامل قبل از اتصال به سیستم واقعی.
5. Vision + action: تبدیل مشاهده دوربین به تصمیم حرکتی، ابتدا در شبیه‌ساز.
6. Typed judgments: خروجی ساختاریافته برای classify/filter/approve به‌جای متن آزاد.
7. Database agent: پرسش طبیعی از داده‌های ARIA با کنترل دسترسی.
8. Idea evaluation: ساخت ابزار تحلیل پروژه‌های درآمدی ARIA بدون اجرای خودکار تصمیم‌های مالی.
9. Robotics roadmap: ابتدا simulation، سپس ESP32-S3 و ربات حرکتی حدود ۵ میلیون تومان.

## معماری پیشنهادی برای ARIA
Observation → State → Reasoning → Proposed Action → Permission Engine → User Approval when required → Execution → Result → Memory

برای عملیات مالی، حذف داده، تغییر credential، deployment و ارسال خارجی تأیید صریح مالک لازم است.

## نکته امنیتی
نمونه‌های معاملاتی یا اتوماسیون خارجی را مستقیماً وارد ARIA نمی‌کنیم. ابتدا در sandbox یا simulation بررسی می‌شوند. کلیدهای API، توکن‌ها، کوکی‌ها و اطلاعات حساس نباید وارد GitHub شوند.

## منبع معرفی‌شده توسط کاربر
پست X با متن ارسالی کاربر:
https://x.com/imryven/status/2102833122198843579
