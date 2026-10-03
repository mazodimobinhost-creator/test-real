"""سایت عمومی (Momentum) — همان دامنه‌ی پنل، ظاهر یک کسب‌وکار واقعی.

`/` = سایت اصلی، `/plans` = تعرفه‌ها، `/status` = وضعیت سرویس، `/download` = اپ‌ها،
`/contact` = تماس. پنل روی یک مسیر مخفی بالا می‌آید (پیش‌فرض: خودکار تصادفی).
"""

from __future__ import annotations

import html

from . import store

APPS = [
    ("v2rayNG", "اندروید", "https://github.com/2dust/v2rayNG/releases", "🟢"),
    ("Hiddify", "اندروید / iOS / دسکتاپ", "https://github.com/hiddify/hiddify-next/releases", "🔵"),
    ("Streisand", "iOS / macOS", "https://apps.apple.com/app/streisand/id6450534064", "🍎"),
    ("NekoBox", "اندروید / ویندوز", "https://github.com/MatsuriDayo/NekoBoxForAndroid/releases", "🟣"),
    ("sing-box", "iOS / دسکتاپ", "https://github.com/SagerNet/sing-box/releases", "⚫"),
    ("Shadowrocket", "iOS (پولی)", "https://apps.apple.com/app/shadowrocket/id932747118", "🚀"),
]


def _css(brand: dict) -> str:
    return f"""
:root{{--c1:{brand['color']};--c2:{brand['color2']};--bg:#070a15;--card:#101528;--line:#212a4a;--fg:#eaefff;--mut:#94a2c9}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:Vazirmatn,Tahoma,'Segoe UI',sans-serif;direction:rtl;line-height:1.9}}
a{{color:inherit;text-decoration:none}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 18px}}
header{{position:sticky;top:0;z-index:9;background:rgba(7,10,21,.85);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}}
.nav{{display:flex;align-items:center;gap:20px;padding:15px 0}}
.brand{{font-weight:800;font-size:19px;display:flex;align-items:center;gap:9px}}
.mark{{width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,var(--c1),var(--c2));display:flex;align-items:center;justify-content:center}}
nav.links{{display:flex;gap:18px;margin-inline-start:auto;color:var(--mut);font-size:14px}}
nav.links a:hover{{color:var(--fg)}}
.btn{{display:inline-block;background:linear-gradient(135deg,var(--c1),var(--c2));padding:12px 24px;border-radius:13px;font-weight:700;font-size:14px}}
.btn.ghost{{background:transparent;border:1px solid var(--line);color:var(--fg)}}
.hero{{padding:74px 0 54px;text-align:center}}
.hero h1{{font-size:38px;margin:14px 0 14px;line-height:1.5}}
.hero p{{color:var(--mut);max-width:660px;margin:0 auto 26px;font-size:16px}}
.badge{{display:inline-block;background:#151c36;border:1px solid var(--line);color:var(--mut);font-size:12.5px;padding:6px 13px;border-radius:99px}}
.grid{{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px}}
.card h3{{margin:10px 0 8px;font-size:17px}}
.mut{{color:var(--mut);font-size:13.5px}}
section{{padding:34px 0}}
h2.sec{{font-size:23px;margin:0 0 18px}}
.plan{{position:relative;overflow:hidden}}
.plan .price{{font-size:26px;font-weight:800;color:#8ee6b0;margin:10px 0}}
.plan .tag{{position:absolute;inset-inline-start:0;top:14px;background:linear-gradient(135deg,var(--c1),var(--c2));font-size:11px;padding:4px 12px;border-radius:0 99px 99px 0}}
.bar{{background:linear-gradient(135deg,var(--c1),var(--c2));color:#fff;text-align:center;font-size:13px;padding:9px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{text-align:right;padding:11px 8px;border-bottom:1px solid var(--line)}}
th{{color:var(--mut);font-weight:600;font-size:12.5px}}
.dot{{width:9px;height:9px;border-radius:99px;display:inline-block;background:#22c55e;box-shadow:0 0 10px #22c55e}}
footer{{border-top:1px solid var(--line);color:var(--mut);font-size:13px;padding:26px 0;margin-top:20px}}
.steps li{{margin-bottom:8px}}
"""


def _shell(brand: dict, title: str, body: str, extra_head: str = "") -> str:
    bar = ""
    if brand.get("announce_bar"):
        bar = f'<div class="bar">{html.escape(brand["announce_bar"])}</div>'
    nav = (
        '<a href="/">خانه</a><a href="/plans">تعرفه‌ها</a><a href="/status">وضعیت سرویس</a>'
        '<a href="/download">راهنمای اتصال</a><a href="/contact">تماس</a>'
    )
    return f"""<!doctype html><html lang="fa" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} | {html.escape(brand['name'])}</title>
<meta name="description" content="{html.escape(brand.get('slogan') or '')}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css">
<style>{_css(brand)}</style>{extra_head}</head><body>
{bar}
<header><div class="wrap"><div class="nav">
  <div class="brand"><span class="mark">{html.escape(brand['logo'])}</span> {html.escape(brand['name'])}</div>
  <nav class="links">{nav}</nav>
</div></div></header>
{body}
<footer><div class="wrap">
  © {html.escape(brand['name'])} — {html.escape(brand.get('slogan') or '')}
  {'· <a href="' + html.escape(brand['contact']) + '">پشتیبانی</a>' if brand.get('contact') else ''}
</div></footer></body></html>"""


def _announcements_box(brand: dict) -> str:
    items = store.list_announcements(only_enabled=True)[:3]
    if not items:
        return ""
    colors = {"info": "#4f7cff", "warn": "#f59e0b", "ok": "#22c55e", "bad": "#ef4444"}
    cards = "".join(
        f'<div class="card" style="border-inline-start:3px solid {colors.get(a["level"], "#4f7cff")}">'
        f'<h3>{html.escape(a["title"])}</h3><p class="mut">{html.escape(a["body"])}</p></div>'
        for a in items
    )
    return f'<section><div class="wrap"><h2 class="sec">📣 اطلاع‌رسانی‌ها</h2><div class="grid">{cards}</div></div></section>'


def home(brand: dict) -> str:
    features = brand.get("features") or []
    feat_cards = "".join(
        f'<div class="card"><h3>✅ {html.escape(f)}</h3></div>' for f in features
    ) or '<div class="card"><h3>✅ اتصال سریع</h3></div>'
    plans = store.list_plans(only_enabled=True) if brand.get("show_plans") else []
    plan_cards = ""
    if plans:
        items = "".join(
            f'<div class="card plan"><span class="tag">{"پیشنهاد ویژه" if i == 0 else "پلن"}</span>'
            f'<h3>{html.escape(p["name"])}</h3>'
            f'<div class="price">{html.escape(str(p.get("price") or "—"))}</div>'
            f'<div class="mut">حجم: {"نامحدود" if not p["traffic_gb"] else str(p["traffic_gb"]) + " گیگابایت"}<br>'
            f'مدت: {p["days"]} روز<br>دستگاه هم‌زمان: {p["max_ips"] or "نامحدود"}</div>'
            f'<div style="margin-top:14px"><a class="btn" href="/plans">سفارش</a></div></div>'
            for i, p in enumerate(plans[:3])
        )
        plan_cards = f'<section><div class="wrap"><h2 class="sec">💎 تعرفه‌ها</h2><div class="grid">{items}</div></div></section>'

    status = store.stats_overview()
    body = f"""
<section class="hero"><div class="wrap">
  <span class="badge">🔒 اتصال امن و رمزنگاری‌شده</span>
  <h1>{html.escape(brand.get('hero') or brand['name'])}</h1>
  <p>{html.escape(brand.get('slogan') or '')}</p>
  <a class="btn" href="/plans">مشاهده تعرفه‌ها</a>
  <a class="btn ghost" href="/download" style="margin-inline-start:8px">راهنمای اتصال</a>
</div></section>
<section><div class="wrap"><div class="grid">{feat_cards}
  <div class="card"><h3>🌍 لوکیشن‌های فعال</h3><p class="mut">{status['online_locations']} لوکیشن آنلاین</p></div>
</div></div></section>
{plan_cards}
{_announcements_box(brand)}"""
    return _shell(brand, "خانه", body)


def plans_page(brand: dict) -> str:
    plans = store.list_plans(only_enabled=True)
    if not plans:
        body = (
            '<section><div class="wrap"><div class="card"><h3>تعرفه‌ای ثبت نشده است</h3>'
            '<p class="mut">برای خرید با پشتیبانی در تماس باشید.</p></div></div></section>'
        )
    else:
        cards = "".join(
            f'<div class="card plan"><h3>{html.escape(p["name"])}</h3>'
            f'<div class="price">{html.escape(str(p.get("price") or "—"))}</div>'
            f'<ul class="mut" style="padding-inline-start:18px">'
            f'<li>حجم: {"نامحدود" if not p["traffic_gb"] else str(p["traffic_gb"]) + " گیگابایت"}</li>'
            f'<li>مدت: {p["days"]} روز</li>'
            f'<li>دستگاه هم‌زمان: {p["max_ips"] or "نامحدود"}</li>'
            f'{("<li>سرعت: " + str(p["speed_kbps"]) + " kbps</li>") if p["speed_kbps"] else ""}'
            f'</ul><a class="btn" href="{html.escape(brand.get("contact") or "/")}">همین حالا سفارش بده</a></div>'
            for p in plans
        )
        body = f'<section><div class="wrap"><h2 class="sec">تعرفه‌ها</h2><div class="grid">{cards}</div></div></section>'
    return _shell(brand, "تعرفه‌ها", body)


def status_page(brand: dict) -> str:
    locs = store.list_locations()
    rows_list = []
    for loc in locs:
        online_html = '<span class="dot"></span> آنلاین' if store.location_is_online(loc) else '🔴 در دسترس نیست'
        rows_list.append(
            f'<tr><td>{html.escape(loc["flag"])} {html.escape(loc["name"])}</td>'
            f'<td>{html.escape(loc.get("region") or "—")}</td>'
            f'<td>{online_html}</td></tr>'
        )
    rows = "".join(rows_list) or '<tr><td colspan="3" class="mut">لوکیشنی ثبت نشده است</td></tr>'
    stats = store.stats_overview()
    body = f"""<section><div class="wrap">
  <h2 class="sec">وضعیت سرویس</h2>
  <div class="grid" style="margin-bottom:18px">
    <div class="card"><h3>لوکیشن‌های آنلاین</h3><p>{stats['online_locations']} از {stats['locations']}</p></div>
    <div class="card"><h3>کاربران فعال</h3><p>{stats['active_users']}</p></div>
    <div class="card"><h3>ترافیک ۲۴ ساعت</h3><p>{round(stats['total_traffic'] / 1024**2, 1)} مگابایت</p></div>
  </div>
  <div class="card"><table><thead><tr><th>لوکیشن</th><th>ریجن</th><th>وضعیت</th></tr></thead><tbody>{rows}</tbody></table></div>
</div></section>"""
    return _shell(brand, "وضعیت سرویس", body)


def download_page(brand: dict) -> str:
    cards = "".join(
        f'<div class="card"><h3>{icon} {html.escape(name)}</h3><p class="mut">{html.escape(platform)}</p>'
        f'<a class="btn ghost" href="{html.escape(url)}" target="_blank" rel="noopener">دریافت</a></div>'
        for name, platform, url, icon in APPS
    )
    body = f"""<section><div class="wrap">
  <h2 class="sec">راهنمای اتصال</h2>
  <div class="card" style="margin-bottom:18px">
    <ol class="steps">
      <li>لینک اشتراکی که برایتان ارسال شده را کپی کنید.</li>
      <li>یکی از اپ‌های زیر را نصب کنید.</li>
      <li>در اپ، بخش «اشتراک» یا Subscription را باز کنید و لینک را وارد کنید (Add / Import).</li>
      <li>به‌روزرسانی بزنید؛ کانفیگ همه‌ی لوکیشن‌ها خودکار اضافه می‌شود. نزدیک‌ترین سرور را انتخاب کنید.</li>
    </ol>
  </div>
  <div class="grid">{cards}</div>
</div></section>"""
    return _shell(brand, "راهنمای اتصال", body)


def contact_page(brand: dict) -> str:
    body = f"""<section><div class="wrap"><h2 class="sec">تماس با ما</h2>
  <div class="card">
    <p class="mut">برای خرید، پیگیری سفارش یا مشکل فنی از راه‌های زیر در ارتباط باش.</p>
    {'<p>💬 پشتیبانی: <a href="' + html.escape(brand['contact']) + '">' + html.escape(brand['contact']) + '</a></p>' if brand.get('contact') else ''}
    {'<p>👤 مسئول سرویس: ' + html.escape(brand['card_holder']) + '</p>' if brand.get('card_holder') else ''}
    {'<p>💳 شماره کارت: <code>' + html.escape(brand['card_number']) + '</code></p>' if brand.get('card_number') else ''}
  </div></div></section>"""
    return _shell(brand, "تماس", body)


def countdown_page(brand: dict) -> str:
    body = """<section class="hero"><div class="wrap">
  <h1>به‌زودی برمی‌گردیم</h1>
  <p>سرویس در حال بروزرسانی است. چند دقیقه‌ی دیگر دوباره سر بزنید.</p>
  <div id="t" style="font-size:26px;font-weight:800">۰۰:۰۰</div>
</div></section>
<script>
var s = 15 * 60;
setInterval(function(){ s = Math.max(0, s - 1);
  var m = String(Math.floor(s/60)).padStart(2,'0'), q = String(s%60).padStart(2,'0');
  document.getElementById('t').textContent = m + ':' + q;
  if (s === 0) location.reload();
}, 1000);
</script>"""
    return _shell(brand, "بروزرسانی", body)


def robots_txt(brand: dict) -> str:
    return "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /sub/\n"


def sitemap_xml(base: str) -> str:
    paths = ["/", "/plans", "/status", "/download", "/contact"]
    urls = "".join(f"<url><loc>{base}{p}</loc></url>" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
