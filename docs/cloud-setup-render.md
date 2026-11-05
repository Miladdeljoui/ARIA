# انتقال استقرار ARIA از Render به Weblines

راهنمای قدیمی Render به‌روز نیست. برای کاربران ایران، راهنمای جاری استقرار را در [deploy-weblines-iran.md](deploy-weblines-iran.md) دنبال کن.

خلاصهٔ تنظیم کنونی:
- Backend: `cloud/aria_cloud.py` (FastAPI داخل `cloud/Dockerfile`)
- درگاه مدل: AvalAI، آدرس اصلی `https://api.avalai.ir/v1/chat/completions`
- آدرس جایگزین مستند داخل ایران: `https://api.avalapis.ir/v1/chat/completions` (فقط در خطای اتصال)
- مدل متن پیش‌فرض: `deepseek-flash`
- تصویر: `muse-image-1.0`
- کلیپ: `veo-3.1-fast-generate-001`
- تولید رسانه عمداً خاموش است تا صاحب پروژه کلید، اعتبار و سقف هزینه را در سرور تنظیم کند.

**هیچ کلید API را در APK یا GitHub ذخیره نکن.** برای آزمایش یا فروش، از فضای ذخیره‌سازی پایدار برای `/data/aria_cloud.db` استفاده کن. وضعیت اشتراک و پرداخت زرین‌پال هنوز کامل نشده است و تا آزمون callback واقعی، دریافت پول از کاربر مجاز نیست.
