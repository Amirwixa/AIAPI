# AI Agent Hub (اپلیکیشن چت با ایجنت‌های هوش مصنوعی)

یک اپلیکیشن بومی و مدرن اندروید (Native Android) توسعه‌یافته با **Kotlin** و **Jetpack Compose (Material 3)** جهت اتصال به ارائه‌دهندگان مختلف هوش مصنوعی و گفتگو با ایجنت‌های دلخواه با شخصیت‌ها و مدل‌های سفارشی.

---

## قابلیت‌های کلیدی (Key Features)

1. **مدیریت چندگانه ایجنت‌ها (Multi-Agent Management):**
   - تعریف نامحدود ایجنت با نام، آیکون، و هویت سفارشی
   - تنظیم دستورالعمل سیستمی (System Prompt) برای تعیین کاراکتر و رفتار هر ایجنت
   - پشتیبانی از ویرایش و حذف ایجنت‌ها
2. **پشتیبانی دوگانه از معماری‌های API:**
   - **ساختار OpenAI-Compatible:** قابل استفاده برای OpenAI (GPT-4o, GPT-4o-mini)، OpenRouter، DeepSeek، Groq، Claude (از طریق پروکسی/روتر) و سرورهای محلی نظیر Ollama / vLLM / LM Studio.
   - **ساختار Google Gemini:** پشتیبانی مستقیم از API بومی گوگل (مانند `gemini-2.5-flash`، `gemini-1.5-pro` و غیره).
3. **پشتیبانی از بینایی ماشین و ارسال تصویر (Vision Support):**
   - قابلیت انتخاب تصویر از گالری، پیش‌نمایش، فشرده‌سازی خودکار و ارسال همزمان متن و تصویر برای مدل‌های چندوجهی.
4. **ذخیره‌سازی دائمی تاریخچه گفتگوها (Persistent Local History):**
   - ذخیره سابقه چت هر ایجنت به‌صورت مجزا در فایل‌های امن داخلی (`chat_<agentId>.json`).
   - دکمه پاکسازی تاریخچه مکالمه برای هر ایجنت به صورت مستقل.
5. **رابط کاربری جذاب و مدرن (Modern UI):**
   - طراحی‌شده با Jetpack Compose و تم تیره (Dark Theme).
   - چیدمان راست‌به‌چپ (RTL) متناسب با زبان فارسی.
   - قابلیت کپی کردن پیام‌ها با یک لمس (Touch to Copy).
6. **پیکربندی ساخت خودکار (CI/CD با GitHub Actions):**
   - قابلیت کامپایل و دانلود مستقیم فایل APK بدون نیاز به نصب Android Studio یا Java روی سیستم کاربر.

---

## ساختار پروژه (Directory Structure)

```
ai-agent-hub/
├── .github/
│   └── workflows/
│       └── build.yml               # خودکارسازی ساخت فایل نصبی APK در گیت‌هاب
├── app/
│   ├── build.gradle.kts            # تنظیمات ماژول اپلیکیشن و وابستگی‌ها
│   ├── proguard-rules.pro          # قوانین Proguard برای کامپایل بهینه
│   └── src/
│       └── main/
│           ├── AndroidManifest.xml # مجوزهای برنامه (اینترنت و غیره)
│           └── java/
│               └── com/example/aiagentchat/
│                   └── MainActivity.kt # کد کامل برنامه، مدیریت وضعیت و ارتباط شبکه
├── gradle/
│   └── wrapper/
│       └── gradle-wrapper.properties
├── build.gradle.kts                # تنظیمات ریشه پروژه
├── settings.gradle.kts             # تعریف ماژول‌ها و مخازن
├── gradle.properties               # حافظه JVM و تنظیمات کامپایلر اندروید
├── gradlew                         # اسکریپت اجرای گریدل در لینوکس و مک
├── gradlew.bat                     # اسکریپت اجرای گریدل در ویندوز
├── .gitignore
└── README.md
```

---

## راهنمای تنظیم ایجنت‌ها برای ارائه‌دهندگان مختلف

### ۱. Google Gemini
- **نوع ارائه‌دهنده (Provider):** `Gemini`
- **آدرس سرور (Base URL):** `https://generativelanguage.googleapis.com/v1beta/models`
- **نام مدل (Model ID):** `gemini-2.5-flash` یا `gemini-1.5-pro`
- **کلید API:** کلید دریافت‌شده از [Google AI Studio](https://aistudio.google.com/)

### ۲. OpenAI
- **نوع ارائه‌دهنده (Provider):** `OpenAI / OpenRouter`
- **آدرس سرور (Base URL):** `https://api.openai.com/v1/chat/completions`
- **نام مدل (Model ID):** `gpt-4o-mini` یا `gpt-4o`
- **کلید API:** کلید دریافت‌شده از پنل OpenAI

### ۳. OpenRouter (دسترسی به تمامی مدل‌ها نظیر Claude 3.5 Sonnet, DeepSeek R1 و ...)
- **نوع ارائه‌دهنده (Provider):** `OpenAI / OpenRouter`
- **آدرس سرور (Base URL):** `https://openrouter.ai/api/v1/chat/completions`
- **نام مدل (Model ID):** `anthropic/claude-3.5-sonnet` یا `deepseek/deepseek-r1`
- **کلید API:** کلید دریافت‌شده از OpenRouter

### ۴. DeepSeek
- **نوع ارائه‌دهنده (Provider):** `OpenAI / OpenRouter`
- **آدرس سرور (Base URL):** `https://api.deepseek.com/v1/chat/completions`
- **نام مدل (Model ID):** `deepseek-chat`
- **کلید API:** کلید اختصاصی DeepSeek

### ۵. Groq (سرعت پاسخ‌دهی فوق‌العاده بالا)
- **نوع ارائه‌دهنده (Provider):** `OpenAI / OpenRouter`
- **آدرس سرور (Base URL):** `https://api.groq.com/openai/v1/chat/completions`
- **نام مدل (Model ID):** `llama-3.3-70b-versatile`
- **کلید API:** کلید دریافتی از Groq Console

### ۶. سرورهای محلی (Local LLM via Ollama / LM Studio)
- **نوع ارائه‌دهنده (Provider):** `OpenAI / OpenRouter`
- **آدرس سرور (Base URL):** `http://<IP-سیستم-شما>:11434/v1/chat/completions`
- **نام مدل (Model ID):** `llama3.2` یا `qwen2.5`
- **کلید API:** مقدار دلخواه (مثلاً `ollama`)

---

## نحوه ساخت و نصب فایل APK

### روش اول: ساخت آنلاین در GitHub (پیشنهادی - بدون نیاز به ابزار محلی)
1. پوشه پروژه را در یک مخزن جدید در حساب کاربری GitHub خود Push کنید.
2. به تب **Actions** در مخزن گیت‌هاب بروید.
3. پروسه `Build Android APK` به صورت خودکار اجرا می‌شود (یا می‌توانید با زدن دکمه `Run workflow` آن را به صورت دستی آغاز کنید).
4. پس از اتمام اجرا (حدود ۲ تا ۳ دقیقه)، فایل نصبی `AI-Agent-Hub-APK.zip` در بخش Artifacts قابل دانلود است.

### روش دوم: باز کردن در Android Studio
1. برنامه **Android Studio** را باز کنید.
2. گزینه **Open** را انتخاب کرده و این پوشه (`ai-agent-hub`) را انتخاب نمایید.
3. اجازه دهید فرایند Gradle Sync به پایان برسد.
4. دکمه سبز رنگ **Run** را بزنید تا برنامه روی شبیه‌ساز (Emulator) یا گوشی واقعی شما نصب و اجرا شود.

### روش سوم: کامپایل از طریق ترمینال (خط فرمان)
در ویندوز:
```powershell
.\gradlew.bat assembleDebug
```
در لینوکس / مک:
```bash
./gradlew assembleDebug
```
فایل APK خروجی در مسیر زیر قرار می‌گیرد:
`app/build/outputs/apk/debug/app-debug.apk`
