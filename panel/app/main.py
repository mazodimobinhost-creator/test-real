"""پنل مرکزی — FastAPI app.

مسیرها:
  /                     سایت عمومی (Momentum) — یا حالت countdown
  /plans /status /download /contact   صفحات سایت
  /sub/<token>          لینک اشتراک (base64 برای کلاینت، HTML برای مرورگر)
  <secret_path>         پنل مدیریت (مسیر تصادفی مخفی، از تب «برند» قابل تغییر)
  /go                   میان‌بر به پنل مدیریت
  /api/admin/*          API پنل،  /api/node/*  API نودها
"""

from __future__ import annotations

import asyncio
import base64
import logging

from fastapi import Cookie, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

from . import adminapi, bot, marketing, nodeapi, store, subpage, tutorial, ui
from .settings import APP_NAME, APP_TITLE_FA, APP_VERSION, NODE_SYNC_INTERVAL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("mlp.panel")

app = FastAPI(title=APP_NAME, version=APP_VERSION, docs_url=None, redoc_url=None)
app.include_router(adminapi.router)
app.include_router(nodeapi.router)

_offline_notified: set[int] = set()


@app.on_event("startup")
async def on_startup() -> None:
    store.init_db()
    store.log_event("panel", f"پنل {APP_NAME} v{APP_VERSION} روشن شد (مسیر پنل: {store.secret_path()})", "ok")
    bot.start_bot()
    asyncio.create_task(_watcher())
    logger.info("panel started · data dir=%s · admin path=%s", store.settings.DATA_DIR, store.secret_path())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await bot.stop_bot()


@app.middleware("http")
async def detect_public_url(request: Request, call_next):
    """اگر دامنه‌ی عمومی دستی ست نشده باشد، از هدرهای پروکسی تشخیص می‌دهیم."""
    try:
        if not store.get_setting("public_base_url") and not store.public_base():
            host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
            if host and "localhost" not in host and "127.0.0.1" not in host:
                scheme = request.headers.get("x-forwarded-proto") or "https"
                store.set_setting("public_base_url", f"{scheme}://{host}")
                store.log_event("panel", f"دامنه‌ی عمومی خودکار تشخیص داده شد: {scheme}://{host}", "info")
    except Exception:
        pass
    return await call_next(request)


async def _watcher() -> None:
    """وضعیت لوکیشن‌ها + بستن کاربران تمام‌شده."""
    while True:
        try:
            for loc in store.list_locations(only_enabled=True):
                online = store.location_is_online(loc)
                if not online and loc["id"] not in _offline_notified and loc.get("last_seen"):
                    store.log_event("location", f"لوکیشن «{loc['name']}» آفلاین شد", "warn")
                    _offline_notified.add(loc["id"])
                elif online:
                    _offline_notified.discard(loc["id"])
            for user in store.query("SELECT * FROM users"):
                u = dict(user)
                status = store.user_status(u)
                if status in ("limited", "expired") and int(u.get("enabled") or 0):
                    store.log_event("user", f"کاربر «{u['name']}» {status} شد و غیرفعال گردید", "warn")
                    store.execute("UPDATE users SET enabled=0 WHERE id=?", (u["id"],))
        except Exception as exc:
            logger.warning("watcher error: %s", exc)
        await asyncio.sleep(NODE_SYNC_INTERVAL * 2)


# ───────────────────────────── سلامت ─────────────────────────────
@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "mlp-panel", "version": APP_VERSION, "role": "panel"}


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return marketing.robots_txt(store.brand())


@app.get("/sitemap.xml")
async def sitemap():
    base = store.public_base() or ""
    return Response(content=marketing.sitemap_xml(base), media_type="application/xml")


# ───────────────────────────── سایت عمومی ─────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home():
    brand = store.brand()
    if brand.get("site_mode") == "countdown":
        return HTMLResponse(marketing.countdown_page(brand))
    return HTMLResponse(marketing.home(brand))


@app.get("/plans", response_class=HTMLResponse)
async def plans():
    return HTMLResponse(marketing.plans_page(store.brand()))


@app.get("/status", response_class=HTMLResponse)
async def status():
    return HTMLResponse(marketing.status_page(store.brand()))


@app.get("/download", response_class=HTMLResponse)
async def download():
    return HTMLResponse(marketing.download_page(store.brand()))


@app.get("/contact", response_class=HTMLResponse)
async def contact():
    return HTMLResponse(marketing.contact_page(store.brand()))


@app.get("/api/site")
async def site_api():
    brand = store.brand()
    return {
        "ok": True,
        "brand": brand,
        "plans": [
            {"name": p["name"], "days": p["days"], "traffic_gb": p["traffic_gb"], "price": p["price"]}
            for p in store.list_plans(only_enabled=True)
        ],
        "announcements": [
            {"title": a["title"], "body": a["body"], "level": a["level"]}
            for a in store.list_announcements(only_enabled=True)
        ],
        "status": store.stats_overview(),
    }


@app.get("/api")
async def api_root():
    return {"ok": True, "service": "mlp-panel", "version": APP_VERSION}


# ───────────────────────────── پنل مدیریت ─────────────────────────────
def _panel_title() -> str:
    return store.get_setting("panel_title") or store.brand().get("name") or APP_TITLE_FA


@app.get("/go")
async def go_to_panel():
    return RedirectResponse(store.secret_path() or "/", status_code=307)


@app.get("/dashboard")
async def legacy_dashboard():
    return RedirectResponse(store.secret_path() or "/", status_code=307)


# ───────────────────────────── لینک اشتراک ─────────────────────────────
@app.get("/sub/{token}")
async def subscription(token: str, request: Request):
    user = store.get_user_by_sub(token)
    if not user:
        return HTMLResponse(
            "<html dir='rtl'><body style='background:#0b1020;color:#eaf0ff;font-family:Tahoma;text-align:center;padding:60px'>"
            "<h2>لینک اشتراک پیدا نشد</h2><p>این لینک نامعتبر یا حذف شده است.</p></body></html>",
            status_code=404,
        )
    query = dict(request.query_params)
    ua = request.headers.get("user-agent", "")
    accept = request.headers.get("accept", "")
    fmt = (query.get("format") or "").lower()

    if query.get("stats") or query.get("info"):
        return JSONResponse(subpage.page_json(user))
    if fmt == "plain":
        return PlainTextResponse(subpage.build_text(user), media_type="text/plain; charset=utf-8")
    if fmt == "base64":
        return PlainTextResponse(subpage.build_b64(user), media_type="text/plain; charset=utf-8")
    if subpage.is_browser(ua, accept):
        return HTMLResponse(subpage.page_html(user))

    title = store.get_setting("panel_title") or store.brand().get("name") or APP_NAME
    try:
        title.encode("latin-1")
        profile_title = title
    except UnicodeEncodeError:
        profile_title = "base64:" + base64.b64encode(title.encode("utf-8")).decode("ascii")
    return PlainTextResponse(
        subpage.build_b64(user),
        media_type="text/plain; charset=utf-8",
        headers={
            "Profile-Title": profile_title,
            "Profile-Update-Interval": "12",
            "Subscription-Userinfo": _userinfo_header(user),
        },
    )


def _userinfo_header(user: dict) -> str:
    limit = int(user.get("limit_bytes") or 0)
    used = int(user.get("used_bytes") or 0)
    expire = int(user.get("expire_at") or 0)
    return f"upload=0; download={used}; total={limit}; expire={expire}"


# ───────────────────────────── مسیر مخفی پنل و ۴۰۴ (باید آخر ثبت شود) ─────────────────────────────
@app.get("/{path:path}", response_class=HTMLResponse)
async def catch_all(path: str, request: Request, mlp_sid: str | None = Cookie(default=None)):
    """مسیر مخفی پنل + هر مسیر ناشناخته."""
    admin_path = store.secret_path()
    clean = "/" + path.strip("/")
    if clean == admin_path or clean.startswith(admin_path + "/"):
        if not store.get_session(mlp_sid or ""):
            return HTMLResponse(ui.login_html(_panel_title(), admin_path))
        return HTMLResponse(ui.app_html(_panel_title(), admin_path))
    if store.brand().get("site_mode") == "countdown":
        return HTMLResponse(marketing.countdown_page(store.brand()), status_code=200)
    return HTMLResponse(marketing.home(store.brand()), status_code=404)
