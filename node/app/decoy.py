"""سایت پوششی (Decoy) — نود و پنل به‌جای پاسخ‌های مشکوک، یک سایت واقعی نشان می‌دهند.

هدف: اگر کسی دامنه‌ی نود را در مرورگر باز کند یا اسکنر روی آن در بزند، چیزی شبیه
یک وب‌سایت معمولی ببیند (فروشگاه، شرکت، وبلاگ) — نه پنل و نه پیام خطای پروکسی.
"""

from __future__ import annotations

import os
import random

SITE_KINDS = ("shop", "corp", "blog")

DEFAULT_BRANDS = {
    "shop": "دیجی‌استور",
    "corp": "آریان سیستم",
    "blog": "وبلاگ تازه‌ها",
}

PRODUCTS = [
    ("هدفون بی‌سیم پرو", "۱٫۲۵۰٫۰۰۰", "🎧"),
    ("ساعت هوشمند اسپرت", "۲٫۹۸۰٫۰۰۰", "⌚"),
    ("پاوربانک ۲۰٬۰۰۰", "۸۹۰٫۰۰۰", "🔋"),
    ("کیبورد مکانیکی", "۱٫۶۵۰٫۰۰۰", "⌨️"),
    ("اسپیکر بلوتوثی", "۷۴۰٫۰۰۰", "🔊"),
    ("ماوس گیمینگ", "۵۶۰٫۰۰۰", "🖱️"),
]

POSTS = [
    ("راهنمای انتخاب هدفون مناسب برای ورزش", "۱۴۰۵/۰۷/۰۲", "اگر هنگام دویدن از هدفون استفاده می‌کنید، سه فاکتور مهم است: وزن، ثبات و ضدآب بودن…"),
    ("ساعت هوشمند؛ از کدام برند شروع کنیم؟", "۱۴۰۵/۰۶/۲۵", "بازار ساعت‌های هوشمند شلوغ است. در این نوشته سه رده‌ی قیمتی را بررسی می‌کنیم…"),
    ("چطور عمر باتری پاوربانک را بیشتر کنیم؟", "۱۴۰۵/۰۶/۱۱", "چند عادت ساده باعث می‌شود پاوربانک سال‌ها سالم بماند…"),
]

SERVICES = [
    ("مشاوره و راه‌اندازی", "طراحی و پیاده‌سازی زیرساخت شبکه و سرور"),
    ("پشتیبانی ۲۴/۷", "تیم فنی همیشه در دسترس برای مشتریان سازمانی"),
    ("توسعه نرم‌افزار", "سامانه‌های تحت وب و اپلیکیشن‌های موبایل"),
]

BASE_CSS = """
:root{--bg:#0f1220;--card:#171b2e;--line:#252b47;--fg:#e9edff;--mut:#98a3c9;--acc:#4f7cff;--acc2:#8b5cf6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:'Vazirmatn',Tahoma,'Segoe UI',sans-serif;direction:rtl;line-height:1.8}
a{color:inherit;text-decoration:none}
header{position:sticky;top:0;background:rgba(15,18,32,.88);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);z-index:5}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px}
.nav{display:flex;align-items:center;gap:18px;padding:14px 0}
.brand{font-weight:800;font-size:19px;display:flex;align-items:center;gap:9px}
.mark{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,var(--acc),var(--acc2));display:flex;align-items:center;justify-content:center;font-size:15px}
nav.links{display:flex;gap:16px;margin-inline-start:auto;color:var(--mut);font-size:14px}
nav.links a:hover{color:var(--fg)}
.hero{padding:64px 0 42px;text-align:center}
.hero h1{font-size:32px;margin:0 0 12px;line-height:1.5}
.hero p{color:var(--mut);max-width:640px;margin:0 auto 22px}
.btn{display:inline-block;background:linear-gradient(135deg,var(--acc),var(--acc2));padding:11px 22px;border-radius:12px;font-weight:700;font-size:14px}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));padding-bottom:40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px}
.card h3{margin:6px 0 8px;font-size:16px}
.mut{color:var(--mut);font-size:13px}
.price{font-weight:800;color:#8ee6b0;margin-top:8px;display:block}
section{padding:10px 0 30px}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:13px;padding:22px 0;text-align:center}
.badge{display:inline-block;background:#1e2440;color:var(--mut);font-size:12px;padding:4px 10px;border-radius:99px;margin-bottom:10px}
"""


def _brand(kind: str) -> str:
    return os.environ.get("MLP_DECOY_NAME") or DEFAULT_BRANDS.get(kind, "شرکت نمونه")


def _nav(kind: str) -> str:
    if kind == "shop":
        return '<a href="/">خانه</a><a href="/products">محصولات</a><a href="/about">درباره ما</a><a href="/contact">تماس</a>'
    if kind == "blog":
        return '<a href="/">خانه</a><a href="/posts">نوشته‌ها</a><a href="/about">درباره</a>'
    return '<a href="/">خانه</a><a href="/services">خدمات</a><a href="/about">درباره</a><a href="/contact">تماس</a>'


def _shell(kind: str, title: str, body: str, status: int = 200) -> tuple[str, int]:
    brand = _brand(kind)
    html = f"""<!doctype html><html lang="fa" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | {brand}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css">
<style>{BASE_CSS}</style></head><body>
<header><div class="wrap"><div class="nav">
  <div class="brand"><span class="mark">◆</span> {brand}</div>
  <nav class="links">{_nav(kind)}</nav>
</div></div></header>
{body}
<footer><div class="wrap">© {brand} · همه‌ی حقوق محفوظ است.</div></footer>
</body></html>"""
    return html, status


def _home(kind: str, brand_hint: str = "") -> tuple[str, int]:
    brand = brand_hint or _brand(kind)
    if kind == "shop":
        cards = "".join(
            f'<div class="card"><div style="font-size:30px">{icon}</div><h3>{name}</h3>'
            f'<span class="mut">ارسال سریع به تمام کشور</span><span class="price">{price} تومان</span></div>'
            for name, price, icon in PRODUCTS
        )
        body = f"""<section class="hero"><div class="wrap">
          <span class="badge">ارسال رایگان بالای ۵۰۰ هزار تومان</span>
          <h1>فروشگاه {brand}</h1>
          <p>جدیدترین گجت‌ها و لوازم جانبی دیجیتال با ضمانت اصالت کالا و هفت روز مهلت بازگشت.</p>
          <a class="btn" href="/products">مشاهده محصولات</a></div></section>
          <section><div class="wrap"><div class="grid">{cards}</div></div></section>"""
    elif kind == "blog":
        cards = "".join(
            f'<div class="card"><span class="mut">{date}</span><h3>{title}</h3><p class="mut">{body_text}</p>'
            f'<a class="btn" href="/posts" style="padding:8px 16px;font-size:13px">ادامه مطلب</a></div>'
            for title, date, body_text in POSTS
        )
        body = f"""<section class="hero"><div class="wrap">
          <h1>{brand}</h1><p>یادداشت‌ها و راهنماهای کوتاه درباره‌ی گجت‌ها، شبکه و بهره‌وری.</p></div></section>
          <section><div class="wrap"><div class="grid">{cards}</div></div></section>"""
    else:
        cards = "".join(
            f'<div class="card"><h3>{name}</h3><p class="mut">{desc}</p></div>' for name, desc in SERVICES
        )
        body = f"""<section class="hero"><div class="wrap">
          <span class="badge">از سال ۱۳۹۲ در کنار شما</span>
          <h1>{brand}</h1>
          <p>ارائه‌دهنده‌ی راهکارهای زیرساخت، شبکه و نرم‌افزار برای کسب‌وکارهای کوچک و متوسط.</p>
          <a class="btn" href="/contact">درخواست مشاوره</a></div></section>
          <section><div class="wrap"><div class="grid">{cards}</div></div></section>"""
    return _shell(kind, "خانه", body)


def _page(kind: str, path: str) -> tuple[str, int]:
    clean = "/" + path.strip("/")
    if clean in ("/", ""):
        return _home(kind)
    if kind == "shop" and clean == "/products":
        cards = "".join(
            f'<div class="card"><div style="font-size:30px">{icon}</div><h3>{name}</h3>'
            f'<span class="price">{price} تومان</span></div>'
            for name, price, icon in PRODUCTS
        )
        return _shell(kind, "محصولات", f'<section><div class="wrap"><h2>محصولات</h2><div class="grid">{cards}</div></div></section>')
    if kind == "blog" and clean == "/posts":
        cards = "".join(
            f'<div class="card"><span class="mut">{date}</span><h3>{title}</h3><p class="mut">{text}</p></div>'
            for title, date, text in POSTS
        )
        return _shell(kind, "نوشته‌ها", f'<section><div class="wrap"><h2>نوشته‌ها</h2><div class="grid">{cards}</div></div></section>')
    if clean == "/about":
        text = (
            "ما تیمی کوچک از مهندسان نرم‌افزار و شبکه هستیم که از سال ۱۳۹۲ روی پروژه‌های زیرساختی کار می‌کنیم. "
            "تمرکز ما روی پایداری، امنیت و پشتیبانی واقعی است."
        )
        return _shell(kind, "درباره ما", f'<section><div class="wrap"><div class="card"><h3>درباره {_brand(kind)}</h3><p class="mut">{text}</p></div></div></section>')
    if clean == "/contact":
        return _shell(
            kind,
            "تماس با ما",
            '<section><div class="wrap"><div class="card"><h3>راه‌های ارتباطی</h3>'
            '<p class="mut">تلفن: ۰۲۱-۹۱۰۰۰۰۰۰<br>ایمیل: info@example.com<br>'
            'ساعات پاسخ‌گویی: شنبه تا چهارشنبه ۹ تا ۱۸</p></div></div></section>',
        )
    if kind == "corp" and clean == "/services":
        cards = "".join(f'<div class="card"><h3>{n}</h3><p class="mut">{d}</p></div>' for n, d in SERVICES)
        return _shell(kind, "خدمات", f'<section><div class="wrap"><h2>خدمات</h2><div class="grid">{cards}</div></div></section>')
    return not_found(kind)


def not_found(kind: str = "corp") -> tuple[str, int]:
    body = (
        '<section class="hero"><div class="wrap"><h1>۴۰۴ — صفحه پیدا نشد</h1>'
        '<p>نشانی وارد‌شده وجود ندارد یا حذف شده است. از منوی بالا صفحه‌ی مورد نظر را انتخاب کنید.</p>'
        '<a class="btn" href="/">بازگشت به خانه</a></div></section>'
    )
    return _shell(kind, "صفحه پیدا نشد", body, status=404)


# نوع انتخابی از پنل (باندل sync) — بر env اولویت دارد اگر env صریح نباشد
KIND_OVERRIDE: str | None = None


def set_kind(kind: str | None) -> None:
    """تعیین نوع سایت پوششی از سمت پنل (بدون ری‌استارت)."""
    global KIND_OVERRIDE
    kind = (kind or "").strip().lower()
    KIND_OVERRIDE = kind if kind in SITE_KINDS else None


def choose_kind() -> str:
    kind = (os.environ.get("MLP_DECOY") or "auto").strip().lower()
    if kind in SITE_KINDS:
        return kind
    if KIND_OVERRIDE:
        return KIND_OVERRIDE
    if kind in ("none", "off", "0"):
        return "none"
    # انتخاب پایدار بر اساس دامنه/نام سرویس تا با هر ری‌استارت عوض نشود
    seed = (os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("MLP_NODE_NAME") or "web")
    rnd = random.Random(seed)
    return rnd.choice(SITE_KINDS)


def decoy_response(path: str) -> tuple[str, int]:
    kind = choose_kind()
    if kind == "none":
        return "", 204
    return _page(kind, path)
