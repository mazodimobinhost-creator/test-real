"""پنل مرکزی مولتی‌لوکیشن — FastAPI app."""

from __future__ import annotations

import asyncio
import base64
import logging

from fastapi import Cookie, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from . import adminapi, bot, nodeapi, store, subpage, ui
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
    store.log_event("panel", f"پنل {APP_NAME} v{APP_VERSION} روشن شد", "ok")
    bot.start_bot()
    asyncio.create_task(_watcher())
    logger.info("panel started · data dir=%s", store.settings.DATA_DIR)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await bot.stop_bot()


async def _watcher() -> None:
    """هر ۳۰ ثانیه وضعیت لوکیشن‌ها را بررسی و کاربران تمام‌شده را علامت‌گذاری می‌کند."""
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
                    store.log_event("user", f"کاربر «{u['name']}» {status} شد و از لوکیشن‌ها قطع می‌شود", "warn")
                    store.execute("UPDATE users SET enabled=0 WHERE id=?", (u["id"],))
        except Exception as exc:
            logger.warning("watcher error: %s", exc)
        await asyncio.sleep(NODE_SYNC_INTERVAL * 2)


@app.get("/healthz", response_class=JSONResponse)
async def healthz():
    return {"ok": True, "service": "mlp-panel", "version": APP_VERSION, "role": "panel"}


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


def _title() -> str:
    return store.get_setting("panel_title") or APP_TITLE_FA


@app.get("/", response_class=HTMLResponse)
async def root(mlp_sid: str | None = Cookie(default=None)):
    if not store.get_session(mlp_sid or ""):
        return HTMLResponse(ui.login_html(_title()))
    return HTMLResponse(ui.app_html(_title()))


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(mlp_sid: str | None = Cookie(default=None)):
    return await root(mlp_sid)


@app.get("/api")
async def api_root():
    return {"ok": True, "service": "mlp-panel", "version": APP_VERSION}


# ───────────────────────────── لینک اشتراک ─────────────────────────────────
def _sub_routes() -> list[str]:
    settings = store.all_settings()
    sub_path = (settings.get("sub_path") or "sub").strip("/")
    return [f"/{sub_path}/{{token}}", f"/{{token}}"]

# مسیر پیش‌فرض /sub/{token} ؛ اگر sub_path عوض شود، همان مسیر جدید فعال می‌شود.


@app.get("/sub/{token}")
async def subscription(token: str, request: Request):
    return await _serve_sub(token, request)


@app.get("/{token}")
async def subscription_short(token: str, request: Request):
    return await _serve_sub(token, request)


async def _serve_sub(token: str, request: Request):
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
    body = subpage.build_b64(user)
    title = store.get_setting("panel_title") or APP_NAME
    try:
        title.encode("latin-1")
        profile_title = title
    except UnicodeEncodeError:
        profile_title = "base64:" + base64.b64encode(title.encode("utf-8")).decode("ascii")
    return PlainTextResponse(
        body,
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
