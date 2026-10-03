"""ربات تلگرام (بدون کتابخانه‌ی جانبی، با Long Polling روی HTTP)."""

from __future__ import annotations

import asyncio
import html
from typing import Any

import httpx

from . import orders, store
from .subpage import build_text, page_json
from .settings import APP_VERSION

API_BASE = "https://api.telegram.org"
_client: httpx.AsyncClient | None = None
_task: asyncio.Task | None = None
_offset = 0
_pending_plan: dict[str, int] = {}   # chat_id -> plan_id
_started_for_token = ""


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(40.0, connect=10.0))
    return _client


def _token() -> str:
    return (store.get_setting("bot_token") or "").strip()


def _admin_ids() -> list[str]:
    raw = store.get_setting("bot_admin_ids") or ""
    return [x.strip() for x in raw.replace("،", ",").split(",") if x.strip()]


def _is_admin(chat_id: Any) -> bool:
    return str(chat_id) in _admin_ids()


async def api(method: str, payload: dict | None = None) -> dict:
    token = _token()
    if not token:
        return {"ok": False, "description": "bot token not set"}
    try:
        resp = await _http().post(f"{API_BASE}/bot{token}/{method}", json=payload or {})
        return resp.json()
    except Exception as exc:
        return {"ok": False, "description": f"{type(exc).__name__}: {exc}"}


async def send(chat_id: Any, text: str, keyboard: dict | None = None, markdown: bool = False) -> dict:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": True,
    }
    if markdown:
        payload["parse_mode"] = "HTML"
    if keyboard:
        payload["reply_markup"] = keyboard
    return await api("sendMessage", payload)


def _kb(rows: list[list[tuple[str, str]]]) -> dict:
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}


# ───────────────────────────── متن‌ها ──────────────────────────────────────
def _welcome() -> str:
    settings = store.all_settings()
    template = settings.get("bot_text_start") or "سلام 👋"
    return template.format(panel=settings.get("panel_title") or "پنل")


def _account_text(user: dict) -> str:
    data = page_json(user)
    lines = [
        f"👤 <b>{html.escape(data['name'] or 'کاربر')}</b>",
        f"وضعیت: <b>{data['status_fa']}</b>",
        f"مصرف: <b>{data['used_h']}</b> از <b>{data['limit_h']}</b>",
        f"باقی‌مانده: <b>{data['remaining_h']}</b>",
        f"اعتبار: <b>{'نامحدود' if data['days_left'] is None else str(data['days_left']) + ' روز'}</b>",
        "",
        f"🔗 لینک اشتراک:\n<code>{html.escape(data['sub_url'] or '—')}</code>",
    ]
    if data["configs"]:
        lines.append("")
        lines.append("لوکیشن‌ها: " + " · ".join(f"{c['flag']} {c['location']}" for c in data["configs"]))
    return "\n".join(lines)


def _plans_keyboard() -> dict | None:
    plans = store.list_plans(only_enabled=True)
    if not plans:
        return None
    rows = []
    for plan in plans:
        price = f" · {plan['price']}" if plan.get("price") else ""
        traffic = f"{plan['traffic_gb']}GB" if plan.get("traffic_gb") else "نامحدود"
        rows.append([(f"{plan['name']} | {traffic} | {plan['days']} روز{price}", f"buy:{plan['id']}")])
    return _kb(rows)


# ───────────────────────────── هندلرها ────────────────────────────────────
async def handle_update(update: dict) -> None:
    if "message" in update:
        await _handle_message(update["message"])
    elif "callback_query" in update:
        await _handle_callback(update["callback_query"])


async def _handle_message(message: dict) -> None:
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    who = message.get("from", {}).get("username") or message.get("from", {}).get("first_name") or str(chat_id)
    tg_id = str(message.get("from", {}).get("id") or chat_id)

    if text.startswith("/start"):
        user = store.get_user_by_telegram(tg_id)
        if user:
            await send(chat_id, _account_text(user), _kb([[("🛍 خرید / تمدید", "plans")]]), markdown=True)
            return
        await send(chat_id, _welcome(), _kb([[("🛍 پلن‌ها", "plans"), ("❓ پشتیبانی", "support")]]), markdown=True)
        return

    if text.startswith("/me"):
        user = store.get_user_by_telegram(tg_id)
        if not user:
            await send(chat_id, "حسابی با این آیدی پیدا نشد. برای خرید /plans را بزنید.")
            return
        await send(chat_id, _account_text(user), markdown=True)
        return

    if text.startswith("/plans") or text.startswith("/buy"):
        await _send_plans(chat_id)
        return

    if text.startswith("/support"):
        await send(chat_id, f"پشتیبانی: {store.get_setting('support_url') or '—'}")
        return

    # ── دستورات ادمین ──
    if text.startswith("/stats") and _is_admin(tg_id):
        s = store.stats_overview()
        await send(
            chat_id,
            f"📊 <b>وضعیت پنل</b>\nکاربران: {s['users']} (فعال {s['active_users']})\n"
            f"لوکیشن‌ها: {s['online_locations']}/{s['locations']} آنلاین\n"
            f"سفارش در انتظار: {s['pending_orders']}\n"
            f"کل ترافیک: {round(s['total_traffic'] / 1024**2, 2)} MB",
            markdown=True,
        )
        return

    if text.startswith("/nodes") and _is_admin(tg_id):
        locs = store.list_locations()
        lines = ["🛰 <b>لوکیشن‌ها</b>"]
        for loc in locs:
            online = "🟢" if store.location_is_online(loc) else "🔴"
            st = loc.get("status") or {}
            extra = f" · {st.get('connections', 0)} اتصال" if st else ""
            lines.append(f"{online} {loc['flag']} {loc['name']} ({loc['host'] or 'بدون دامنه'}){extra}")
        await send(chat_id, "\n".join(lines) or "لوکیشنی ثبت نشده", markdown=True)
        return

    if text.startswith("/adduser") and _is_admin(tg_id):
        parts = text.split()
        name = parts[1] if len(parts) > 1 else f"user-{tg_id[-4:]}"
        gb = float(parts[2]) if len(parts) > 2 else 0
        days = int(parts[3]) if len(parts) > 3 else 30
        user_id = store.save_user(
            {
                "name": name,
                "limit_bytes": int(gb * 1024**3),
                "expire_at": store.days_from_now_ts(days),
                "enabled": True,
            }
        )
        store.enable_user_on_all_locations(user_id)
        user = store.get_user(user_id) or {}
        await send(chat_id, _account_text(user), markdown=True)
        return

    # ── دریافت رسید ──
    if str(chat_id) in _pending_plan and (message.get("photo") or message.get("document")):
        plan_id = _pending_plan.pop(str(chat_id))
        plan = store.get_plan(plan_id) or {}
        file_id = ""
        if message.get("photo"):
            file_id = message["photo"][-1].get("file_id", "")
        elif message.get("document"):
            file_id = message["document"].get("file_id", "")
        order_id = store.create_order(tg_id, who, plan_id, receipt=file_id, note=plan.get("name") or "")
        await send(chat_id, f"✅ رسید شما ثبت شد (سفارش #{order_id}). پس از تأیید، لینک اشتراک برایتان ارسال می‌شود.")
        await _notify_admins(order_id, who, plan)
        return

    if text and not text.startswith("/"):
        await send(chat_id, "برای دیدن پلن‌ها /plans و برای حساب من /me را بزنید.")


async def _send_plans(chat_id: Any) -> None:
    kb = _plans_keyboard()
    if not kb:
        await send(chat_id, "در حال حاضر پلن فعالی برای فروش تعریف نشده است.")
        return
    await send(chat_id, "🛍 یک پلن را انتخاب کنید:", kb)


async def _notify_admins(order_id: int, who: str, plan: dict) -> None:
    lines = [
        f"🧾 <b>سفارش جدید #{order_id}</b>",
        f"کاربر: {html.escape(str(who))}",
        f"پلن: {html.escape(str(plan.get('name') or '-'))} · {plan.get('traffic_gb', 0)}GB · {plan.get('days', 0)} روز",
        f"قیمت: {html.escape(str(plan.get('price') or '-'))}",
    ]
    kb = _kb([[(f"✅ تأیید #{order_id}", f"ord:approve:{order_id}"), (f"❌ رد #{order_id}", f"ord:reject:{order_id}")]])
    for admin in _admin_ids():
        await send(admin, "\n".join(lines), kb, markdown=True)


async def _handle_callback(cb: dict) -> None:
    data = cb.get("data") or ""
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    tg_id = str(cb.get("from", {}).get("id") or "")
    await api("answerCallbackQuery", {"callback_query_id": cb.get("id")})

    if data == "plans":
        await _send_plans(chat_id)
        return
    if data == "support":
        await send(chat_id, f"پشتیبانی: {store.get_setting('support_url') or '—'}")
        return
    if data.startswith("buy:"):
        if store.get_setting("bot_sales_enabled") != "1":
            await send(chat_id, "فروش خودکار فعلاً غیرفعال است.")
            return
        plan_id = int(data.split(":", 1)[1])
        plan = store.get_plan(plan_id)
        if not plan:
            await send(chat_id, "این پلن دیگر موجود نیست.")
            return
        _pending_plan[str(chat_id)] = plan_id
        await send(
            chat_id,
            f"🧾 پلن انتخابی: <b>{html.escape(plan['name'])}</b>\n"
            f"حجم: {plan['traffic_gb']}GB · مدت: {plan['days']} روز\n"
            f"مبلغ: {html.escape(str(plan.get('price') or '-'))}\n\n"
            f"لطفاً پس از پرداخت، <b>عکس رسید</b> را همین‌جا ارسال کنید.",
            markdown=True,
        )
        return
    if data.startswith("ord:") and _is_admin(tg_id):
        _, action, order_id_raw = data.split(":", 2)
        order_id = int(order_id_raw)
        order = store.get_order(order_id) or {}
        if action == "approve":
            result = orders.fulfill_order(order_id, f"ادمین {tg_id}")
            if not result.get("ok"):
                await send(chat_id, f"⚠️ {result.get('error')}")
                return
            await send(chat_id, f"✅ سفارش #{order_id} تأیید شد ({result.get('action')}).")
            await _deliver(result.get("user") or {}, order)
        elif action == "reject":
            orders.reject_order(order_id, "رد توسط ادمین", f"ادمین {tg_id}")
            await send(chat_id, f"❌ سفارش #{order_id} رد شد.")
            await send(order.get("telegram_id"), f"❌ سفارش #{order_id} تأیید نشد. برای پیگیری با پشتیبانی در تماس باشید.")
        return


async def _deliver(user: dict, order: dict) -> None:
    tg = str(order.get("telegram_id") or user.get("telegram_id") or "")
    if not tg:
        return
    text = _account_text(user)
    await send(tg, f"🎉 سفارش شما تأیید شد!\n\n{text}", markdown=True)


async def notify_order_decision(order_id: int, approved: bool, extra: str = "") -> None:
    order = store.get_order(order_id) or {}
    tg = str(order.get("telegram_id") or "")
    if not tg:
        return
    if approved:
        user = store.get_user_by_telegram(tg)
        if user:
            await send(tg, f"🎉 سفارش #{order_id} تأیید شد.\n\n{_account_text(user)}", markdown=True)
        else:
            await send(tg, f"🎉 سفارش #{order_id} تأیید شد.\n{extra}")
    else:
        await send(tg, f"❌ سفارش #{order_id} تأیید نشد. {extra}")


async def broadcast_message(text: str) -> dict:
    sent = 0
    failed = 0
    for row in store.query("SELECT DISTINCT telegram_id FROM users WHERE telegram_id != ''"):
        res = await send(row["telegram_id"], text)
        if res.get("ok"):
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)
    store.log_event("bot", f"پیام همگانی: {sent} موفق / {failed} ناموفق", "info")
    return {"ok": True, "sent": sent, "failed": failed}


async def bot_selfcheck() -> dict:
    token = _token()
    if not token:
        return {"ok": False, "error": "توکن ربات تنظیم نشده است"}
    res = await api("getMe")
    if not res.get("ok"):
        return {"ok": False, "error": res.get("description") or "خطای ناشناخته"}
    me = res.get("result", {})
    hook = await api("deleteWebhook", {"drop_pending_updates": False})
    return {
        "ok": True,
        "username": me.get("username"),
        "name": me.get("first_name"),
        "webhook_cleared": bool(hook.get("ok")),
        "admins": len(_admin_ids()),
        "version": APP_VERSION,
    }


# ───────────────────────────── حلقه‌ی Long Polling ───────────────────────
async def _poll_loop() -> None:
    global _offset, _started_for_token
    while True:
        token = _token()
        if not token or store.get_setting("bot_enabled") != "1":
            await asyncio.sleep(5)
            continue
        if token != _started_for_token:
            _started_for_token = token
            res = await api("deleteWebhook", {"drop_pending_updates": True})
            store.log_event("bot", f"ربات فعال شد (webhook پاک شد: {bool(res.get('ok'))})", "ok")
        try:
            resp = await _http().get(
                f"{API_BASE}/bot{token}/getUpdates",
                params={"offset": _offset, "timeout": 25, "allowed_updates": '["message","callback_query"]'},
                timeout=httpx.Timeout(40.0, connect=10.0),
            )
            data = resp.json()
            if not data.get("ok"):
                await asyncio.sleep(4)
                continue
            for update in data.get("result", []):
                _offset = max(_offset, int(update.get("update_id", 0)) + 1)
                try:
                    await handle_update(update)
                except Exception as exc:
                    store.log_event("bot", f"خطا در پردازش آپدیت: {type(exc).__name__}: {exc}", "error")
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(3)


def start_bot() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_poll_loop())


async def stop_bot() -> None:
    global _task, _client
    if _task:
        _task.cancel()
        _task = None
    if _client is not None:
        await _client.aclose()
        _client = None
