"""تکمیل سفارش‌ها: تبدیل پلن به کاربر واقعی."""

from __future__ import annotations

from . import store
from .subpage import build_text


def fulfill_order(order_id: int, decided_by: str = "admin") -> dict:
    """سفارش را تأیید و کاربرش را می‌سازد (یا تمدید می‌کند). خروجی: اطلاعات کاربر + متن ساب."""
    order = store.get_order(order_id)
    if not order:
        return {"ok": False, "error": "سفارش پیدا نشد"}
    if order["status"] == "approved":
        return {"ok": False, "error": "این سفارش قبلاً تأیید شده"}

    plan = store.get_plan(int(order["plan_id"] or 0)) or {}
    telegram_id = str(order.get("telegram_id") or "")
    traffic_bytes = int(float(plan.get("traffic_gb") or 0) * 1024**3)
    days = int(plan.get("days") or 0)

    user = store.get_user_by_telegram(telegram_id) if telegram_id else None
    if user:
        # تمدید: حجم و زمان به مقدار فعلی اضافه می‌شود
        base_limit = int(user.get("limit_bytes") or 0)
        new_limit = base_limit + traffic_bytes if (base_limit or traffic_bytes) else 0
        base_expire = max(int(user.get("expire_at") or 0), int(__import__("time").time()))
        new_expire = base_expire + days * 86400 if days else base_expire
        store.save_user(
            {
                "id": user["id"],
                "name": user.get("name") or order.get("who") or "user",
                "limit_bytes": new_limit,
                "expire_at": new_expire,
                "max_ips": int(plan.get("max_ips") or user.get("max_ips") or 0),
                "speed_kbps": int(plan.get("speed_kbps") or user.get("speed_kbps") or 0),
                "enabled": True,
                "telegram_id": telegram_id,
                "note": user.get("note") or "",
            }
        )
        user_id = int(user["id"])
        action = "تمدید"
    else:
        user_id = store.save_user(
            {
                "name": (order.get("who") or f"tg{telegram_id}")[:60],
                "limit_bytes": traffic_bytes,
                "expire_at": store.days_from_now_ts(days),
                "max_ips": int(plan.get("max_ips") or 0),
                "speed_kbps": int(plan.get("speed_kbps") or 0),
                "enabled": True,
                "telegram_id": telegram_id,
                "note": f"سفارش #{order_id} · {plan.get('name') or ''}",
            }
        )
        store.enable_user_on_all_locations(user_id)
        action = "ایجاد"

    store.set_order_status(order_id, "approved", f"توسط {decided_by}")
    store.log_event("order", f"سفارش #{order_id} تأیید شد ({action} کاربر) توسط {decided_by}", "ok")

    user = store.get_user(user_id) or {}
    return {
        "ok": True,
        "user_id": user_id,
        "action": action,
        "user": user,
        "sub_url": _sub_url(user),
        "text": build_text(user),
    }


def reject_order(order_id: int, reason: str, decided_by: str = "admin") -> dict:
    order = store.get_order(order_id)
    if not order:
        return {"ok": False, "error": "سفارش پیدا نشد"}
    store.set_order_status(order_id, "rejected", f"{reason} · {decided_by}")
    store.log_event("order", f"سفارش #{order_id} رد شد: {reason}", "warn")
    return {"ok": True}


def _sub_url(user: dict) -> str:
    settings = store.all_settings()
    base = store.public_base()
    sub_path = settings.get("sub_path") or "sub"
    if not base:
        return ""
    return f"{base}/{sub_path}/{user.get('sub_token')}"
