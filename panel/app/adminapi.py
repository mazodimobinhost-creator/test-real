"""API مدیریتی پنل (JSON) — مصرف‌کننده‌ی آن رابط کاربری وب است."""

from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request
from pydantic import BaseModel

from . import geoinfo, nodeapi, orders, store
from .security import hash_password, verify_password
from .settings import APP_VERSION

router = APIRouter(prefix="/api/admin")
COOKIE = "mlp_sid"

# ── محدودسازی تلاش ورود (brute-force) ──
_LOGIN_FAILS: dict[str, list] = {}
LOGIN_LIMIT = 8
LOGIN_WINDOW = 600.0


def require_admin(mlp_sid: str | None = Cookie(default=None)) -> dict:
    session = store.get_session(mlp_sid or "")
    if not session:
        raise HTTPException(status_code=401, detail="unauthorized")
    return session


class LoginIn(BaseModel):
    username: str = ""
    password: str = ""


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _login_blocked(ip: str) -> bool:
    import time as _t

    rec = _LOGIN_FAILS.get(ip)
    if not rec:
        return False
    count, first = rec
    if _t.time() - first > LOGIN_WINDOW:
        _LOGIN_FAILS.pop(ip, None)
        return False
    return count >= LOGIN_LIMIT


def _login_failed(ip: str) -> None:
    import time as _t

    now = _t.time()
    count, first = _LOGIN_FAILS.get(ip, (0, now))
    if now - first > LOGIN_WINDOW:
        count, first = 0, now
    _LOGIN_FAILS[ip] = (count + 1, first)


@router.post("/login")
async def login(body: LoginIn, request: Request):
    ip = _client_ip(request)
    if _login_blocked(ip):
        raise HTTPException(status_code=429, detail="تلاش‌های ناموفق زیاد بود؛ چند دقیقه بعد امتحان کن")
    settings = store.all_settings()
    expected_user = (settings.get("admin_user") or "admin").strip()
    if body.username.strip() and body.username.strip() != expected_user:
        store.log_event("auth", f"تلاش ورود با نام کاربری نادرست: {body.username[:30]}", "warn")
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز نادرست است")
    if not verify_password(body.password, settings.get("admin_password_hash") or ""):
        _login_failed(ip)
        store.log_event("auth", f"تلاش ناموفق ورود از {ip}", "warn")
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز نادرست است")
    _LOGIN_FAILS.pop(ip, None)
    sid = store.create_session(ip)
    store.log_event("auth", "ورود موفق به پنل", "ok")
    resp = {"ok": True, "sid": sid}
    from fastapi.responses import JSONResponse

    out = JSONResponse(resp)
    out.set_cookie(COOKIE, sid, httponly=True, samesite="lax", max_age=7 * 86400, path="/")
    return out


@router.post("/logout")
async def logout(mlp_sid: str | None = Cookie(default=None)):
    if mlp_sid:
        store.delete_session(mlp_sid)
    from fastapi.responses import JSONResponse

    out = JSONResponse({"ok": True})
    out.delete_cookie(COOKIE, path="/")
    return out


@router.get("/me")
async def me(_=None):
    return {"ok": True, "user": store.get_setting("admin_user"), "version": APP_VERSION}


# ───────────────────────────── داشبورد ──────────────────────────────────────
@router.get("/overview")
async def overview(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    locs = store.list_locations()
    now = store.now_ts()
    for loc in locs:
        loc["online"] = store.location_is_online(loc)
        loc["seen_ago"] = now - int(loc.get("last_seen") or 0) if loc.get("last_seen") else None
    return {
        "ok": True,
        "stats": store.stats_overview(),
        "locations": locs,
        "traffic": store.hourly_traffic(24),
        "events": store.list_events(30),
        "server_time": now,
        "version": APP_VERSION,
    }


# ───────────────────────────── لوکیشن‌ها ────────────────────────────────────
class LocationIn(BaseModel):
    id: int | None = None
    name: str = ""
    flag: str = "🌍"
    region: str = ""
    host: str = ""
    transports: list[str] = ["ws"]
    ws_path: str = "/ws"
    xhttp_path: str = "/xhttp"
    tcp_port: int = 0
    cf_host: str = ""
    engine: str = "python"
    decoy: str = ""
    egress_mode: str = "direct"
    egress: dict = {}
    clean_ip: str = ""
    clean_sni: str = ""
    enabled: bool = True
    sort: int = 0
    note: str = ""


@router.get("/locations")
async def locations_list(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    locs = store.list_locations()
    now = store.now_ts()
    for loc in locs:
        loc["online"] = store.location_is_online(loc)
        loc["seen_ago"] = (now - int(loc["last_seen"])) if loc["last_seen"] else None
        loc["env"] = nodeapi.node_env_snippet(loc, store.public_base())
    return {"ok": True, "locations": locs}


@router.post("/locations")
async def locations_save(body: LocationIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    is_new = not body.id
    loc_id = store.save_location(body.model_dump())
    if is_new:
        # کاربران موجود روی لوکیشن جدید هم فعال شوند
        for user in store.query("SELECT id FROM users"):
            store.execute(
                "INSERT OR IGNORE INTO user_locations (user_id, location_id, enabled) VALUES (?,?,1)",
                (user["id"], loc_id),
            )
        store.log_event("location", f"لوکیشن «{body.name}» ساخته شد", "ok")
    loc = store.get_location(loc_id)
    return {"ok": True, "location": loc, "env": nodeapi.node_env_snippet(loc, store.public_base())}


@router.delete("/locations/{loc_id}")
async def locations_delete(loc_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    loc = store.get_location(loc_id)
    store.delete_location(loc_id)
    store.log_event("location", f"لوکیشن «{(loc or {}).get('name', loc_id)}» حذف شد", "warn")
    return {"ok": True}


@router.post("/locations/{loc_id}/rotate")
async def locations_rotate(loc_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    token = store.rotate_location_token(loc_id)
    loc = store.get_location(loc_id)
    store.log_event("location", f"توکن لوکیشن «{(loc or {}).get('name', loc_id)}» تغییر کرد", "warn")
    return {"ok": True, "token": token, "env": nodeapi.node_env_snippet(loc, store.public_base())}


# ───────────────────────────── کاربران ─────────────────────────────────────
class UserIn(BaseModel):
    id: int | None = None
    name: str = ""
    reseller_id: int = 0
    limit_gb: float = 0
    days: int = 0
    extend: bool = False
    max_ips: int = 0
    speed_kbps: int = 0
    enabled: bool = True
    note: str = ""
    telegram_id: str = ""
    locations: list[int] | None = None


@router.get("/users")
async def users_list(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    return {"ok": True, "users": store.list_users(), "locations": store.list_locations()}


@router.post("/users")
async def users_save(body: UserIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    limit_bytes = int(body.limit_gb * 1024**3) if body.limit_gb else 0
    expire_at = 0
    if body.id and body.extend:
        current = store.get_user(body.id) or {}
        base_limit = int(current.get("limit_bytes") or 0)
        limit_bytes = (base_limit + limit_bytes) if (base_limit or limit_bytes) else 0
        base_expire = max(int(current.get("expire_at") or 0), int(time.time()))
        expire_at = base_expire + body.days * 86400 if body.days else base_expire
    elif body.days:
        expire_at = store.days_from_now_ts(body.days)
    user_id = store.save_user(
        {
            "id": body.id,
            "name": body.name,
            "limit_bytes": limit_bytes,
            "expire_at": expire_at,
            "max_ips": body.max_ips,
            "speed_kbps": body.speed_kbps,
            "enabled": body.enabled,
            "note": body.note,
            "telegram_id": body.telegram_id,
            "reseller_id": body.reseller_id,
            "locations": body.locations,
        }
    )
    if not body.id:
        store.enable_user_on_all_locations(user_id)
        store.log_event("user", f"کاربر «{body.name}» ساخته شد", "ok")
    return {"ok": True, "user": store.get_user(user_id)}


@router.delete("/users/{user_id}")
async def users_delete(user_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    user = store.get_user(user_id)
    store.delete_user(user_id)
    store.log_event("user", f"کاربر «{(user or {}).get('name', user_id)}» حذف شد", "warn")
    return {"ok": True}


@router.post("/users/{user_id}/reset")
async def users_reset(user_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    store.reset_user_usage(user_id)
    store.execute("DELETE FROM usage_marks WHERE user_id=?", (user_id,))
    store.log_event("user", f"مصرف کاربر #{user_id} صفر شد", "warn")
    return {"ok": True}


@router.post("/users/{user_id}/toggle")
async def users_toggle(user_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    user = store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    store.save_user({**user, "enabled": not bool(user["enabled"]), "locations": None})
    return {"ok": True, "enabled": not bool(user["enabled"])}


@router.get("/users/{user_id}/links")
async def users_links(user_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    user = store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    from .subpage import build_text, page_json

    data = page_json(user)
    return {"ok": True, "info": data, "text": build_text(user)}


# ───────────────────────────── پلن‌ها ──────────────────────────────────────
class PlanIn(BaseModel):
    id: int | None = None
    name: str = ""
    days: int = 30
    traffic_gb: float = 0
    price: str = ""
    max_ips: int = 0
    speed_kbps: int = 0
    enabled: bool = True
    sort: int = 0
    reseller_price: int = 0


@router.get("/plans")
async def plans_list(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    return {"ok": True, "plans": store.list_plans()}


@router.post("/plans")
async def plans_save(body: PlanIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    plan_id = store.save_plan(body.model_dump())
    return {"ok": True, "plan": store.get_plan(plan_id)}


@router.delete("/plans/{plan_id}")
async def plans_delete(plan_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    store.delete_plan(plan_id)
    return {"ok": True}


# ───────────────────────────── سفارش‌ها ────────────────────────────────────
@router.get("/orders")
async def orders_list(status: str | None = None, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    return {"ok": True, "orders": store.list_orders(status)}


@router.post("/orders/{order_id}/approve")
async def orders_approve(order_id: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    result = orders.fulfill_order(order_id, "پنل وب")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    from .bot import notify_order_decision

    try:
        await notify_order_decision(order_id, True, result.get("sub_url") or "")
    except Exception as exc:  # ربات ممکن است خاموش باشد
        store.log_event("bot", f"ارسال پیام تأیید ناموفق: {exc}", "warn")
    return result


@router.post("/orders/{order_id}/reject")
async def orders_reject(order_id: int, reason: str = "رد شد", mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    result = orders.reject_order(order_id, reason, "پنل وب")
    from .bot import notify_order_decision

    try:
        await notify_order_decision(order_id, False, reason)
    except Exception:
        pass
    return result


# ───────────────────────────── تنظیمات ─────────────────────────────────────
class SettingsIn(BaseModel):
    panel_title: str | None = None
    site_mode: str | None = None
    brand_name: str | None = None
    brand_slogan: str | None = None
    brand_color: str | None = None
    brand_color2: str | None = None
    brand_logo: str | None = None
    brand_hero: str | None = None
    brand_features: str | None = None
    brand_card_number: str | None = None
    brand_card_holder: str | None = None
    brand_contact: str | None = None
    marketing_show_plans: str | None = None
    announce_bar: str | None = None
    custom_domain: str | None = None
    secret_path: str | None = None
    tutorial_enabled: str | None = None
    config_title: str | None = None
    support_url: str | None = None
    public_base_url: str | None = None
    sub_path: str | None = None
    bot_token: str | None = None
    bot_enabled: str | None = None
    bot_admin_ids: str | None = None
    bot_force_channel: str | None = None
    bot_sales_enabled: str | None = None
    bot_text_start: str | None = None


@router.get("/settings")
async def settings_get(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    data = store.all_settings()
    data.pop("admin_password_hash", None)
    data["detected_base"] = store.public_base()
    return {"ok": True, "settings": data}


@router.post("/settings")
async def settings_save(body: SettingsIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    for key, value in body.model_dump().items():
        if value is not None:
            store.set_setting(key, str(value))
    store.log_event("settings", "تنظیمات به‌روزرسانی شد", "ok")
    return {"ok": True}


class PasswordIn(BaseModel):
    current: str = ""
    new: str = ""


@router.post("/password")
async def password_change(body: PasswordIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    settings = store.all_settings()
    if not verify_password(body.current, settings.get("admin_password_hash") or ""):
        raise HTTPException(status_code=400, detail="رمز فعلی نادرست است")
    if len(body.new) < 6:
        raise HTTPException(status_code=400, detail="رمز جدید باید حداقل ۶ کاراکتر باشد")
    store.set_setting("admin_password_hash", hash_password(body.new))
    store.log_event("auth", "رمز ادمین تغییر کرد", "warn")
    return {"ok": True}


# ───────────────────────────── رویدادها ────────────────────────────────────
@router.get("/events")
async def events_list(limit: int = 100, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    return {"ok": True, "events": store.list_events(min(limit, 500))}


@router.delete("/events")
async def events_clear(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    store.clear_events()
    return {"ok": True}


class BroadcastIn(BaseModel):
    text: str


@router.post("/broadcast")
async def broadcast(body: BroadcastIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    from .bot import broadcast_message

    result = await broadcast_message(body.text)
    return result


@router.post("/bot/test")
async def bot_test(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    from .bot import bot_selfcheck

    return await bot_selfcheck()


# ───────────────────────────── رزیلرها ─────────────────────────────────────
class ResellerIn(BaseModel):
    id: int | None = None
    name: str = ""
    username: str = ""
    password: str = ""
    price_gb: int = 0
    price_day: int = 0
    min_gb: float = 1
    enabled: bool = True
    note: str = ""


@router.get("/resellers")
async def resellers_list(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    out = []
    for r in store.list_resellers():
        r.pop("password_hash", None)
        r["summary"] = store.reseller_user_summary(int(r["id"]))
        out.append(r)
    return {"ok": True, "resellers": out, "plans": store.list_plans()}


@router.post("/resellers")
async def resellers_save(body: ResellerIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    rid = store.save_reseller(body.model_dump())
    store.log_event("reseller", f"رزیلر «{body.name or body.username}» ذخیره شد", "ok")
    reseller = store.get_reseller(rid) or {}
    reseller.pop("password_hash", None)
    return {"ok": True, "reseller": reseller}


@router.delete("/resellers/{rid}")
async def resellers_delete(rid: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    store.delete_reseller(rid)
    return {"ok": True}


class TopupIn(BaseModel):
    reseller_id: int
    amount: int
    note: str = ""
    receipt: str = ""
    status: str = "approved"


@router.post("/resellers/topup")
async def resellers_topup(body: TopupIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    tx_id = store.add_balance(body.reseller_id, body.amount, "topup", body.note, body.receipt, body.status)
    store.log_event("wallet", f"شارژ {body.amount:,} تومانی برای رزیلر #{body.reseller_id}", "ok")
    return {"ok": True, "tx": store.get_tx(tx_id), "balance": store.reseller_balance(body.reseller_id)}


@router.get("/wallet")
async def wallet_list(status: str | None = None, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    txs = store.list_wallet_tx(status)
    return {"ok": True, "txs": txs, "resellers": store.list_resellers()}


@router.post("/wallet/{tx_id}/{action}")
async def wallet_decide(tx_id: int, action: str, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve|reject")
    status = "approved" if action == "approve" else "rejected"
    tx = store.set_tx_status(tx_id, status, "پنل وب")
    if not tx:
        raise HTTPException(status_code=404, detail="تراکنش پیدا نشد")
    await _notify_wallet_decided(tx_id)
    return {"ok": True, "tx": tx}


async def _notify_wallet_decided(tx_id: int) -> None:
    from .bot import send

    tx = store.get_tx(tx_id) or {}
    reseller = store.get_reseller(int(tx.get("reseller_id") or 0)) or {}
    tg = str(reseller.get("note") or "")
    if not (tg.isdigit() and len(tg) > 5):
        return
    if tx.get("status") == "approved":
        await send(tg, f"✅ شارژ کیف پول شما تأیید شد.\nموجودی جدید: {store.reseller_balance(int(reseller['id'])):,} تومان")
    else:
        await send(tg, "❌ درخواست شارژ شما تأیید نشد. با پشتیبانی در تماس باشید.")


# ───────────────────────────── اعلان‌ها ────────────────────────────────────
class AnnounceIn(BaseModel):
    id: int | None = None
    title: str = ""
    body: str = ""
    level: str = "info"
    enabled: bool = True


@router.get("/announcements")
async def announcements_list(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    return {"ok": True, "announcements": store.list_announcements(), "bar": store.get_setting("announce_bar")}


@router.post("/announcements")
async def announcements_save(body: AnnounceIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    aid = store.save_announcement(body.model_dump())
    return {"ok": True, "announcement": store.get_announcement(aid)}


@router.delete("/announcements/{aid}")
async def announcements_delete(aid: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    store.delete_announcement(aid)
    return {"ok": True}


# ───────────────────────────── آموزش راه‌اندازی ─────────────────────────────
@router.get("/tutorial")
async def tutorial_get(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    from . import tutorial

    return {
        "ok": True,
        "steps": [{k: v for k, v in s.items() if k != "files"} for s in tutorial.steps()],
        "files": tutorial.files_payload(),
        "installer": tutorial.installer_command(),
        "box_ip": store.public_base(),
        "secret_path": store.secret_path(),
    }


class TutorialIn(BaseModel):
    key: str
    title: str = ""
    time: str = ""
    text: str = ""
    tip: str = ""
    code: str = ""
    reset: bool = False


@router.post("/tutorial")
async def tutorial_save(body: TutorialIn, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    from . import tutorial

    if body.reset:
        tutorial.reset_step(body.key)
    else:
        tutorial.save_step(body.key, body.model_dump())
    return {"ok": True}


# ───────────────────────────── سلامت و نسخه ────────────────────────────────
@router.get("/brand")
async def brand_get(mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    return {"ok": True, "brand": store.brand(), "secret_path": store.secret_path()}


# ───────────────────────────── مسیر خروج لوکیشن ─────────────────────────────
@router.post("/locations/{lid}/egress-test")
async def location_egress_test(lid: int, mlp_sid: str | None = Cookie(default=None)):
    """تست زنده‌ی مسیر خروج: از نود می‌خواهیم مسیرها را واقعاً امتحان کند."""
    require_admin(mlp_sid)
    location = store.get_location(lid)
    if not location:
        raise HTTPException(status_code=404, detail="لوکیشن پیدا نشد")
    host = (location.get("host") or "").strip()
    if not host:
        raise HTTPException(status_code=400, detail="لوکیشن دامنه‌ای ثبت‌شده ندارد")
    base = host if host.startswith("http") else f"https://{host}"
    url = f"{base.rstrip('/')}/egress?key={location['token']}&test=1"
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"نود پاسخ داد HTTP {resp.status_code}")
        data = resp.json()
        store.log_event("location", f"تست مسیر خروج «{location['name']}» انجام شد", "info")
        return {"ok": True, "node": data.get("egress"), "test": data.get("test"), "source": url}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"نود در دسترس نبود ({type(exc).__name__})؛ وضعیت آخرین گزارش را ببین",
        )


@router.get("/egress/presets")
async def egress_presets(mlp_sid: str | None = Cookie(default=None)):
    """پیش‌تنظیم‌های آماده‌ی مسیر خروج برای استفاده در فرم لوکیشن."""
    require_admin(mlp_sid)
    return {
        "ok": True,
        "presets": [
            {"key": "direct", "title": "مستقیم (خود نود)", "mode": "direct", "egress": {}},
            {"key": "proxy-ip", "title": "پروکسی IP (SOCKS5)", "mode": "proxy",
             "egress": {"proxy": {"type": "socks5h", "list": ["1.2.3.4:1080"], "rotate": "fastest"}}},
            {"key": "proxy-http", "title": "پروکسی IP (HTTP CONNECT)", "mode": "proxy",
             "egress": {"proxy": {"type": "http", "list": ["1.2.3.4:8080"], "rotate": "fastest"}}},
            {"key": "chain-node", "title": "تانل به نود دیگر (VLESS/WS)", "mode": "chain",
             "egress": {"chain": {"host": "node2.example.com", "port": 443, "path": "/ws",
                                  "uuid": "UUID-کاربر-روی-نود-بالادستی", "tls": True, "sni": ""}}},
            {"key": "auto", "title": "خودکار (خروجی تنظیم‌شده، در خرابی مسیر بعدی)", "mode": "auto",
             "egress": {"fallback": True}},
        ],
    }


# ───────────────────────────── IP و موقعیت لوکیشن ─────────────────────────────
async def _node_request(location: dict, path: str, timeout: float = 30.0) -> dict:
    host = (location.get("host") or "").strip()
    if not host:
        raise HTTPException(status_code=400, detail="لوکیشن دامنه ندارد")
    base = host if host.startswith("http") else f"https://{host}"
    last_error = ""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for candidate in (base, base.replace("https://", "http://", 1) if base.startswith("https://") else base):
            url = f"{candidate.rstrip('/')}{path}"
            url = f"{url}{'&' if '?' in url else '?'}key={location['token']}"
            try:
                resp = await client.get(url)
            except Exception as exc:
                last_error = type(exc).__name__
                continue
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception as exc:
                    raise HTTPException(status_code=502, detail=f"پاسخ نود JSON نبود ({type(exc).__name__})")
            last_error = f"HTTP {resp.status_code}"
    raise HTTPException(status_code=502, detail=f"نود پاسخ نداد ({last_error or 'unreachable'})")


@router.post("/locations/{lid}/geo")
async def location_geo(lid: int, mlp_sid: str | None = Cookie(default=None)):
    """IP و موقعیت واقعی خروجی این لوکیشن را از خود نود می‌پرسد."""
    require_admin(mlp_sid)
    location = store.get_location(lid)
    if not location:
        raise HTTPException(status_code=404, detail="لوکیشن پیدا نشد")
    try:
        data = await _node_request(location, "/healthz", timeout=20.0)
        geo = data.get("geo") or {}
        if geo.get("ip"):
            store.save_location_geo(lid, geo)
            store.log_event("location", f"IP لوکیشن «{location['name']}»: {geo['ip']} {geo.get('flag', '')}", "info")
            return {"ok": True, "geo": geo}
        raise HTTPException(status_code=502, detail="نود موقعیت را برنگرداند")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"نود در دسترس نبود ({type(exc).__name__})")


class GeoApplyIn(BaseModel):
    set_flag: bool = True
    set_region: bool = False


@router.post("/locations/{lid}/apply-geo")
async def location_apply_geo(lid: int, body: GeoApplyIn, mlp_sid: str | None = Cookie(default=None)):
    """فلگ/کشور لوکیشن را از IP واقعی خروجی پر می‌کند."""
    require_admin(mlp_sid)
    location = store.get_location(lid)
    if not location:
        raise HTTPException(status_code=404, detail="لوکیشن پیدا نشد")
    data: dict = {}
    if body.set_flag and location.get("geo_flag"):
        data["flag"] = location["geo_flag"]
    if body.set_region and location.get("geo_city"):
        data["region"] = f"{location['geo_city']} · {location.get('geo_country') or ''}".strip(" ·")
    if not data:
        raise HTTPException(status_code=400, detail="چیزی برای اعمال نیست (اول «IP من» را بزن)")
    merged = {**location, **data, "egress": store.location_egress(location),
              "egress_mode": location.get("egress_mode") or "direct",
              "clean_ip": location.get("clean_ip") or "", "clean_sni": location.get("clean_sni") or ""}
    store.save_location(merged)
    return {"ok": True, "location": store.get_location(lid)}


async def orders_refresh_locations() -> None:
    return None


# ───────────────────────────── اسکنر ─────────────────────────────
class ScanIn(BaseModel):
    hosts: str = ""
    port: int = 443
    tls: bool = True
    attempts: int = 3


@router.post("/locations/{lid}/scan")
async def location_scan(lid: int, body: ScanIn, mlp_sid: str | None = Cookie(default=None)):
    """اسکن آی‌پی/هاست‌های کاندید از روی نود (برای پیدا کردن خروجی تمیز و سریع)."""
    require_admin(mlp_sid)
    location = store.get_location(lid)
    if not location:
        raise HTTPException(status_code=404, detail="لوکیشن پیدا نشد")
    hosts = [h.strip() for h in body.hosts.replace("\n", ",").split(",") if h.strip()]
    if not hosts:
        raise HTTPException(status_code=400, detail="لیست آی‌پی/هاست خالی است")
    query = f"/scan?hosts={','.join(hosts[:128])}&port={int(body.port)}&tls={1 if body.tls else 0}&attempts={int(body.attempts)}"
    try:
        data = await _node_request(location, query, timeout=90.0)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"نود در دسترس نبود ({type(exc).__name__})")
    best = data.get("best") or {}
    if best.get("host"):
        store.execute(
            "UPDATE locations SET clean_ip=?, clean_sni=? WHERE id=?",
            (best["host"], (location.get("host") or "").split(":")[0], int(lid)),
        )
        store.log_event("scanner", f"بهترین خروجی برای «{location['name']}»: {best['host']} ({best.get('latency_ms')}ms)", "ok")
    return {"ok": True, "scan": data, "clean_ip": store.get_location(lid, )}


@router.get("/locations/{lid}/clean-ip")
async def location_clean_ip(lid: int, mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    location = store.get_location(lid)
    if not location:
        raise HTTPException(status_code=404, detail="لوکیشن پیدا نشد")
    return {"ok": True, "clean_ip": location.get("clean_ip") or "", "host": location.get("host") or ""}


# ───────────────────────────── راه‌اندازی خودکار (Railway) ─────────────────────────────
class AutoDeployIn(BaseModel):
    token: str = ""
    repo: str = ""
    branch: str = "main"
    project_name: str = ""
    workspace_id: str = ""
    admin_password: str = ""
    node_specs: list[dict] = []
    wait: bool = True


@router.get("/auto-deploy/plan")
async def auto_deploy_plan(repo: str = "", mlp_sid: str | None = Cookie(default=None)):
    require_admin(mlp_sid)
    from . import railway

    saved = store.get_setting("auto_deploy_repo") or ""
    configured = store.get_setting("auto_deploy_token") or ""
    return {
        "ok": True,
        "plan": railway.deploy_plan(repo or saved),
        "has_token": bool(configured),
        "saved_repo": saved,
        "regions": geoinfo.REGION_CHOICES,
        "existing": store.all_settings().get("auto_deploy_result", ""),
        "ssh_note": "بدون توکن هم می‌توانی سرویس‌ها را دستی بسازی؛ ولی با توکن، همه‌چیز خودکار ساخته می‌شود.",
    }


@router.get("/auto-deploy/verify")
async def auto_deploy_verify(token: str = "", mlp_sid: str | None = Cookie(default=None)):
    """توکن Railway را چک می‌کند و نام حساب را برمی‌گرداند (بدون ذخیره)."""
    require_admin(mlp_sid)
    from . import railway

    stored = store.get_setting("auto_deploy_token") or ""
    try:
        async with railway.Railway(token or stored) as client:
            me = await client.me()
        return {"ok": True, "account": me.get("email") or me.get("name") or "ok"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"توکن پذیرفته نشد ({type(exc).__name__})")


@router.post("/auto-deploy/run")
async def auto_deploy_run(body: AutoDeployIn, mlp_sid: str | None = Cookie(default=None)):
    """دکمه‌ی جادویی: با توکن Railway همه‌چیز را می‌سازد."""
    require_admin(mlp_sid)
    from . import railway

    token = (body.token or store.get_setting("auto_deploy_token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="توکن Railway لازم است")
    repo = body.repo or store.get_setting("auto_deploy_repo") or railway.DEFAULT_REPO
    node_specs = [s for s in (body.node_specs or []) if isinstance(s, dict) and s.get("name")]
    public = store.public_base()
    store.set_setting("auto_deploy_token", token)
    store.set_setting("auto_deploy_repo", repo)
    store.log_event("deploy", "راه‌اندازی خودکار روی Railway شروع شد", "info")
    result = await railway.auto_deploy(
        token, repo=repo, branch=body.branch or "main", project_name=body.project_name,
        workspace_id=body.workspace_id, admin_password=body.admin_password,
        node_specs=node_specs or None, panel_url=public, wait=bool(body.wait),
    )
    store.set_setting("auto_deploy_result", railway.to_json({
        "at": store.now_iso(), "project": result.get("project"),
        "panel_url": result.get("panel_url"), "ok": result.get("ok"),
    }))
    level = "ok" if result.get("ok") else "error"
    store.log_event("deploy", f"راه‌اندازی خودکار: {'موفق' if result.get('ok') else 'ناموفق'}", level)
    return result
