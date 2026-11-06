# اتصال ARIA به Paperclip

**وضعیت این تغییر:** راهنمای یکپارچه‌سازی به مخزن ARIA اضافه شده است. خود Paperclip هنوز روی هاست نصب نشده و هیچ عامل عملیاتی از داخل ARIA اجرا نشده است؛ بنابراین این سند، نقشه و تنظیم پیشنهادی است، نه ادعای فعال‌بودن سرویس.

## 1) Paperclip چه چیزی به ARIA اضافه می‌کند؟

[Paperclip](https://github.com/paperclipai/paperclip) یک پنل متن‌باز و قابل‌میزبانی برای مدیریت گروهی از عامل‌های هوش مصنوعی است: ساختار نقش‌ها، هدف‌ها، وظیفه‌ها، زمان‌بندی و heartbeat، بودجه و گزارش هزینه، تأیید انسانی، تاریخچهٔ اجرا و فایل‌های خروجی.

Paperclip خودش مدل هوش مصنوعی یا سرویس رایگانِ همهٔ مدل‌ها نیست. باید یک runtime/agent و یک ارائه‌دهندهٔ مدل به آن متصل شوند. همچنین به‌تنهایی قابلیت ساخت عکس یا کلیپ را به اپ ARIA اضافه نمی‌کند.

## 2) معماری پیشنهادی

```text
اپ اندروید ARIA
      |
      v
ARIA Cloud API  -----> AvalAI (چت فارسی و مدل متنی)
      |
      +---- مسیر رسانهٔ ARIA -----> API ساخت تصویر/ویدئو (با اعتبار و سهمیه)

Paperclip (سرویس وب جداگانه)
      |
      v
OpenCode Agent
      |
      v
AvalAI یا ارائه‌دهندهٔ سازگار دیگر
```

- گفت‌وگوی روزمره، حافظه، حساب کاربر و مسیرهای `/chat`، `/media/image` و `/media/video` در ARIA باقی می‌مانند.
- Paperclip فقط مدیریت عامل‌ها و کارهای چندمرحله‌ای را بر عهده می‌گیرد.
- کد Paperclip را داخل APK کپی نمی‌کنیم؛ پنل آن یک سرویس وب مستقل است و بعداً می‌توان نشانی امن آن را از بخش ابزارهای ARIA باز کرد.
- کلیدهای API فقط در Secrets/Environment سرور نگهداری می‌شوند؛ هرگز داخل APK، فایل عمومی یا GitHub قرار نمی‌گیرند.

## 3) مسیر مدل سازگار با استقرار فعلی ایران

در تنظیم فعلی ARIA، سرویس متنی از AvalAI با endpoint سازگار با الگوی OpenAI استفاده می‌کند. برای عامل Paperclip می‌توان مسیر OpenCode را به همان سرویس هدایت کرد؛ این اتصال باید با حساب و مدل واقعی AvalAI آزمایش شود.

نمونهٔ متغیرهایی که باید در Environment خودِ کانتینر Paperclip ثبت شوند:

**کلید محرمانه**
```dotenv
AVALAI_API_KEY=کلید_واقعی_را_فقط_در_پنل_سرور_وارد_کن
```

**تعریف Provider برای OpenCode**
```json
{
  "avalai": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "AvalAI",
    "options": {
      "baseURL": "https://api.avalai.ir/v1",
      "apiKey": "{env:AVALAI_API_KEY}"
    },
    "models": {
      "deepseek-flash": {
        "name": "DeepSeek Flash"
      }
    }
  }
}
```

این JSON را به‌صورت مقدار متغیر محیطی `PAPERCLIP_OPENCODE_PROVIDERS` ثبت کن. دو مقدار مکمل:

```dotenv
PAPERCLIP_OPENCODE_SMALL_MODEL=avalai/deepseek-flash
OPENCODE_ALLOW_ALL_MODELS=true
```

سپس برای عامل OpenCode از شناسهٔ مدل `avalai/deepseek-flash` استفاده می‌شود. این نمونه بر اساس قرارداد رسمی Paperclip برای `PAPERCLIP_OPENCODE_PROVIDERS` نوشته شده است؛ دسترسی، نام دقیق مدل و سازگاری endpoint باید با یک اجرای آزمایشی تأیید شود. اگر حساب AvalAI نام مدل یا endpoint دیگری ارائه می‌کند، مقادیر بالا باید مطابق پنل همان حساب اصلاح شوند.

**نکتهٔ امنیتی مهم:** عامل‌های محلی OpenCode در اجرای بدون حضور کاربر ممکن است با مجوزهای گسترده اجرا شوند. برای شروع، فقط یک عامل آزمایشی بساز، بودجهٔ پایین بگذار، workspace را به پوشهٔ آزمایشی محدود کن و دسترسی به پرداخت، انتشار، حذف فایل، پیام‌رسانی و Secrets تولیدی را مسدود نگه دار. هر deploy یا اقدام حساس باید تأیید انسانی بخواهد.

اگر استفاده از AvalAI برای یک عامل جواب نداد، می‌توان OpenRouter یا یک gateway سازگار دیگر را به‌عنوان Provider جداگانه امتحان کرد؛ اما رایگان‌بودن، دسترسی از ایران، محدودیت نرخ و کیفیت مدل تضمین‌شده نیست.

## 4) نصب آزمایشی روی سرور Linux

Paperclip طبق راهنمای رسمی از Docker پشتیبانی می‌کند. روی یک میزبان Dockerدار:

```bash
git clone https://github.com/paperclipai/paperclip.git
cd paperclip

export BETTER_AUTH_SECRET="$(openssl rand -hex 32)"
export PAPERCLIP_TOOL_ACTION_SIGNING_SECRET="$(openssl rand -hex 32)"

docker compose -f docker/docker-compose.quickstart.yml up --build
```

در پنل هاست، متغیرهای Provider بخش قبل را نیز به Environment کانتینر اضافه کن. دستور Compose بالا را مطابق نسخهٔ جاری مخزن رسمی اجرا کن؛ فایل‌های Compose را از همان مخزن بگیر و نسخهٔ نصب‌شده را ثبت کن.

پورت پیش‌فرض پنل `3100` است. آن را بدون احراز هویت روی اینترنت عمومی باز نکن. برای استفادهٔ بیرونی، دامنه و HTTPS و ورود امن را از reverse proxy/تنظیمات رسمی Paperclip فعال کن. دیتای Paperclip، پایگاه دادهٔ تعبیه‌شده، فایل‌ها و کلید رمزگذاری Secrets باید روی فضای پایدار ذخیره و از آن نسخهٔ پشتیبان تهیه شود.

## 5) سازگاری با ایران و هزینه

- چون ARIA اکنون روی Weblines مستقر است، گزینهٔ اول بررسی، یک سرویس Docker جداگانه روی همان میزبان یا یک VPS جداگانه است؛ به شرط آنکه هاست Docker Compose، فضای پایدار و منابع کافی بدهد.
- Paperclip و ARIA را بدون بررسی منابع روی پلن کوچک فعلی در یک کانتینر ادغام نکن. عامل‌های هم‌زمان CPU و RAM بیشتری مصرف می‌کنند. حداقل منابع رسمی ثابتی در راهنمای نصب اعلام نشده؛ برای پایلوت، ۲ گیگابایت RAM را فقط نقطهٔ شروع آزمایشی در نظر بگیر و قبل از استفادهٔ چندعاملی مصرف واقعی را اندازه بگیر.
- برای سازگاری از ایران، مهم‌تر از محل دیتاسنتر این است که خود سرور بتواند به دامنهٔ API مدل، GitHub و registry موردنیاز نصب دسترسی پایدار داشته باشد و گوشی هم بتواند دامنهٔ HTTPS پنل را باز کند. این مسیر باید از شبکهٔ واقعی تو تست شود؛ از روی نام کشور میزبان نمی‌توان دسترسی را تضمین کرد.
- سرور ایران با API داخلی مثل AvalAI ممکن است هزینه و دسترسی قابل‌کنترل‌تری داشته باشد؛ ولی نصب اولیه و به‌روزرسانی Paperclip به دریافت سورس/بسته‌ها نیاز دارد.
- Paperclip به‌تنهایی مدل رایگان، اعتبار API، VPS رایگان یا تولید ویدئوی رایگان فراهم نمی‌کند. هزینهٔ سرور، مدل و رسانه جداگانه محاسبه می‌شوند.

## 6) چک‌لیست پذیرش قبل از اتصال به اپ

- [ ] پنل Paperclip با دامنهٔ HTTPS و ورود امن بالا می‌آید.
- [ ] دیتابیس و فایل‌ها پس از restart باقی می‌مانند.
- [ ] کلید AvalAI فقط در Secrets/Environment سرور است.
- [ ] یک عامل آزمایشی با مدل تنظیم‌شده پاسخ واقعی می‌دهد.
- [ ] یک کار آزمایشی در workspace محدود انجام می‌شود و فایل بیرون workspace را تغییر نمی‌دهد.
- [ ] سقف هزینه و توقف عامل‌ها آزمایش می‌شود.
- [ ] دسترسی از اینترنت همراه و اینترنت مورد استفاده در ایران بررسی می‌شود.
- [ ] سپس دربارهٔ افزودن دکمهٔ «مدیریت عامل‌ها» در اپ ARIA تصمیم گرفته می‌شود.

## منابع رسمی

- [Paperclip repository](https://github.com/paperclipai/paperclip)
- [Docker deployment](https://github.com/paperclipai/paperclip-docs/blob/main/docs/reference/deploy/docker.md)
- [OpenCode adapter and custom providers](https://github.com/paperclipai/paperclip-docs/blob/main/docs/reference/adapters/opencode.md)
- [Environment variables](https://github.com/paperclipai/paperclip-docs/blob/main/docs/reference/deploy/environment-variables.md)
