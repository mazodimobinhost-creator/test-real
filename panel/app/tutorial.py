"""آموزش راه‌اندازی داخل پنل + نوشتن خودکار تمام فایل‌های لازم.

هر بخش: توضیح، نکته/هشدار، بلوک کد (قابل کپی) و «دانلود فایل» (لینک
data-URL که سمت مرورگر ساخته می‌شود). محتوای هر بخش در جدول content_blocks
قابل ویرایش و ذخیره است و دکمه‌ی «بازگردانی پیش‌فرض» هم دارد.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import store

ROOT = Path(__file__).resolve().parents[1]          # پوشه‌ی panel
BUNDLE = ROOT / "setup_files.json"                  # ساخته‌شده با tools/gen_setup_files.py
FILES = ["Dockerfile", "railway.toml", "nginx.conf.template", "start-xray.sh", "install-vps.sh"]


def files_payload() -> dict[str, str]:
    """فایل‌های لازم برای راه‌اندازی (بسته‌بندی‌شده در setup_files.json)."""
    try:
        import json as _json

        data = _json.loads(BUNDLE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            return {k: str(v) for k, v in data.items()}
    except Exception:
        pass
    out: dict[str, str] = {}
    for name in FILES:
        try:
            out[name] = (ROOT / name).read_text(encoding="utf-8")
        except Exception:
            continue
    return out


def env_text(kind: str = "panel") -> str:
    base = store.public_base() or "https://panel.up.railway.app"
    if kind == "panel":
        return "\n".join(
            [
                "# --- سرویس پنل ---",
                f"MLP_PUBLIC_URL={base}",
                "MLP_ADMIN_USER=admin",
                "MLP_ADMIN_PASSWORD=یک-رمز-قوی",
                "MLP_DATA_DIR=/data",
                "MLP_ENGINE=python",
            ]
        )
    if kind == "node":
        token = "mlp_xxxxxxxxxxxxxxxx"
        return "\n".join(
            [
                "# --- سرویس نود (هر لوکیشن یک سرویس) ---",
                f"MLP_PANEL_URL={base}",
                f"MLP_NODE_TOKEN={token}",
                "MLP_NODE_NAME=Germany",
                "MLP_NODE_FLAG=🇩🇪",
                "MLP_WS_PATH=/ws",
                "MLP_XHTTP_PATH=/xhttp",
                "MLP_ENGINE=xray",           # برای سرعت بالاتر؛ خالی بگذاری = موتور پایتون
                "MLP_DECOY=auto",            # سایت پوششی: auto | shop | corp | blog | none
            ]
        )
    return ""


def _steps(panel_url: str) -> list[dict]:
    admin = store.secret_path()
    return [
        {
            "key": "step_repo",
            "icon": "①",
            "title": "فورک کردن ریپو",
            "time": "۱ دقیقه",
            "text": "روی گیت‌هاب، بالای صفحه‌ی ریپو دکمه‌ی **Fork** را بزن. بعد از فورک، این پروژه در حساب خودت است و "
                    "می‌توانی هر تغییری بدهی. اگر تغییر خاصی لازم نیست، همین حالا برو مرحله‌ی بعد.",
            "tip": "این پروژه هیچ فایل مخفی یا کلید ثابتی ندارد؛ همه‌ی رمزها از متغیرهای محیطی خوانده می‌شوند.",
            "code": "# اختیاری: کلون و ویرایش محلی\ngit clone https://github.com/<username>/<repo>.git\ncd <repo>",
        },
        {
            "key": "step_panel",
            "icon": "②",
            "title": "ساخت سرویس پنل روی Railway",
            "time": "۲ دقیقه",
            "text": "در Railway یک پروژه بساز و همین ریپو را انتخاب کن. برای این سرویس:\n"
                    "• **Root Directory** را بگذار `panel`\n"
                    "• یک **Volume** روی مسیر `/data` وصل کن (بدون آن همه‌چیز با هر دیپلوی پاک می‌شود)\n"
                    "• در **Networking** یک دامنه بگیر (پورت `8080`)\n"
                    "• متغیرها را طبق فایل زیر ست کن",
            "tip": "رمز پیش‌فرض ادمین `admin` است؛ بعد از اولین ورود از تب «تنظیمات → رمز عبور» عوضش کن. "
                   "مسیر پنل به‌صورت تصادفی مخفی می‌شود تا اسکنرها پیدایش نکنند.",
            "code": env_text("panel"),
        },
        {
            "key": "step_location",
            "icon": "③",
            "title": "ساخت اولین لوکیشن (نود)",
            "time": "۲ دقیقه",
            "text": "یک سرویس دیگر در همان پروژه بساز (همین ریپو) با **Root Directory** = `node`.\n"
                    "• **Region** را انتخاب کن (برای ایران: EU West / Amsterdam)\n"
                    "• دامنه بگیر (پورت `8080`)\n"
                    "• در پنل → تب «لوکیشن‌ها» → «لوکیشن جدید» → نام، فلگ و همان دامنه را بگذار → ذخیره\n"
                    "• روی «متغیرهای نود» بزن و آن‌ها را در Variables سرویس نود بگذار → Deploy",
            "tip": "برای هر لوکیشن جدید فقط همین کار را تکرار کن (سرویس جدید + ریجن جدید + لوکیشن جدید در پنل). "
                   "همه‌ی کانفیگ‌ها خودکار داخل *یک* لینک ساب مشتری می‌آیند.",
            "code": env_text("node"),
        },
        {
            "key": "step_engine",
            "icon": "④",
            "title": "انتخاب موتور: پایتون یا Xray",
            "time": "۱ دقیقه",
            "text": "دو حالت داری:\n"
                    "• **موتور پایتون (پیش‌فرض)**: بدون Xray و بدون nginx؛ محدودیت حجم، انقضا، سرعت و تعداد IP همه اعمال می‌شود.\n"
                    "• **موتور Xray**: سرعت بالاتر و سازگاری کامل با کلاینت‌ها؛ در عوض محدودیت «سرعت» و «تعداد IP» اعمال نمی‌شود (توسط Xray پشتیبانی نمی‌شود).\n\n"
                    "برای Xray در Railway، فایل `Dockerfile.xray` را به‌عنوان Dockerfile ست کن "
                    "(Settings → Build → Dockerfile Path = `node/Dockerfile.xray`) و در لوکیشن پنل، موتور را `xray` بگذار.",
            "tip": "اگر باینری Xray در دسترس نباشد، نود خودکار روی موتور پایتون برمی‌گردد و سرویس قطع نمی‌شود.",
            "code": "MLP_ENGINE=xray\n# مسیرها با nginx داخلی به Xray می‌رسند:\n# NGINX:${PORT} → WS:18080 | XHTTP:18081 | سایت پوششی:8090",
        },
        {
            "key": "step_sub",
            "icon": "⑤",
            "title": "دامنه‌ی اختصاصی برای لینک ساب",
            "time": "۳ دقیقه",
            "text": "دو راه داری:\n"
                    "• **دامنه روی Cloudflare (توصیه‌شده)**: دامنه‌ات را به Cloudflare اضافه کن، یک رکورد `CNAME` مثل `sub.example.com` به دامنه‌ی پنل بزن و "
                    "در Cloudflare گزینه‌ی **Proxied** (ابر نارنجی) را روشن بگذار.\n"
                    "• **دامنه‌ی اختصاصی Railway**: در Settings → Networking → Custom Domain دامنه را اضافه کن و رکورد `CNAME` پیشنهادی را بگذار.\n\n"
                    "بعد در پنل → تنظیمات → «دامنه‌ی عمومی» همان دامنه را بنویس تا لینک ساب با آن ساخته شود.",
            "tip": "دامنه‌ی اختصاصی باعث می‌شود لینک‌ها با دامنه‌ی Railway لو نروند و اگر دامنه فیلتر شد فقط رکورد را عوض کنی.",
            "code": "CNAME  sub  →  <panel-domain>.up.railway.app   (Proxied ✅)",
        },
        {
            "key": "step_bot",
            "icon": "⑥",
            "title": "ربات تلگرام و فروش خودکار",
            "time": "۳ دقیقه",
            "text": "در [@BotFather](https://t.me/BotFather) یک ربات بساز و توکنش را بگیر. "
                    "در پنل → تنظیمات: توکن، آیدی عددی ادمین‌ها (با کاما) را بگذار و «وضعیت ربات» را روشن کن. "
                    "بعد در تب «پلن‌ها» تعرفه‌ها را بساز و در تنظیمات، شماره کارت را وارد کن.",
            "tip": "جریان خرید: مشتری `/start` → پلن → کارت‌به‌کارت → ارسال عکس رسید → تأیید ادمین → لینک ساب خودکار ارسال می‌شود.",
            "code": "/start   → پلن‌ها\n/me      → حساب من\n/stats   → (ادمین) وضعیت\n/nodes   → (ادمین) لوکیشن‌ها\n/adduser name 30 60 → ساخت سریع کاربر",
        },
        {
            "key": "step_test",
            "icon": "⑦",
            "title": "تست نهایی",
            "time": "۲ دقیقه",
            "text": "۱) `https://<node-domain>/` را در مرورگر باز کن؛ باید سایت پوششی (فروشگاه/شرکت) را ببینی — نه پنل و نه خطا.\n"
                    "۲) در پنل، کارت لوکیشن باید سبز (آنلاین) شود.\n"
                    "۳) یک کاربر بساز، «لینک‌ها» را بزن و لینک ساب را در v2rayNG/Hiddify وارد کن.\n"
                    "۴) اگر صفحه‌ی ساب در مرورگر باز می‌شود ولی کلاینت وصل نمی‌شود، مسیرها را چک کن (`/ws` یا `/xhttp`).",
            "tip": "برای عیب‌یابی: `https://<node-domain>/healthz?key=<توکن نود>` جزئیات کامل اتصال نود به پنل را نشان می‌دهد.",
            "code": "curl -s \"https://<panel>/healthz\"\ncurl -s \"https://<node>/healthz?key=<MLP_NODE_TOKEN>\"",
        },
    ]


def steps() -> list[dict]:
    """بخش‌های آموزش با محتوای ذخیره‌شده (اگر مدیر ویرایش کرده باشد)."""
    base = _steps(store.public_base())
    blocks = store.all_blocks()
    out = []
    for item in base:
        override = blocks.get(item["key"])
        merged = dict(item)
        if override:
            try:
                data = json.loads(override)
                if isinstance(data, dict):
                    merged.update({k: v for k, v in data.items() if k in ("title", "time", "text", "tip", "code")})
            except Exception:
                pass
        merged["files"] = files_payload()
        out.append(merged)
    return out


def save_step(key: str, data: dict) -> None:
    clean = {k: str(data.get(k) or "") for k in ("title", "time", "text", "tip", "code")}
    store.set_block(key, json.dumps(clean, ensure_ascii=False))


def reset_step(key: str) -> None:
    store.execute("DELETE FROM content_blocks WHERE key=?", (key,))


def installer_command() -> str:
    """دستور نصب سریع روی VPS (از خودِ ریپوی فورک‌شده)."""
    repo = os.environ.get("MLP_REPO_URL", "").strip()
    if not repo:
        repo = "https://github.com/<your-username>/<your-repo>"
    return (
        f"git clone {repo} mlp && cd mlp && sudo bash node/install-vps.sh"
    )
