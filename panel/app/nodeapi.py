"""API نودها: دریافت bundle و ارسال گزارش مصرف.

نودها همیشه «پول» می‌کنند (pull): با توکن خودشان به پنل وصل می‌شوند. بنابراین
هیچ‌وقت لازم نیست پنل به نود دسترسی ورودی داشته باشد و نیازی به پورت عمومی دوم نیست.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from . import store
from .security import const_time_eq
from .settings import APP_VERSION, NODE_SYNC_INTERVAL

router = APIRouter()


def auth_node(authorization: str = Header(default=""), x_node_token: str = Header(default="")) -> dict:
    token = ""
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_node_token:
        token = x_node_token.strip()
    if not token:
        raise HTTPException(status_code=401, detail="token required")
    loc = store.get_location_by_token(token)
    if not loc:
        raise HTTPException(status_code=401, detail="invalid node token")
    return loc


def _policy_users(location: dict) -> list[dict]:
    out: list[dict] = []
    for row in store.query(
        """SELECT u.* FROM users u JOIN user_locations ul ON ul.user_id=u.id
           WHERE ul.location_id=? AND ul.enabled=1""",
        (location["id"],),
    ):
        user = dict(row)
        status = store.user_status(user)
        out.append(
            {
                "uuid": user["uuid"],
                "name": user["name"],
                "enabled": 1 if status == "active" else 0,
                "status": status,
                "limit_bytes": int(user["limit_bytes"] or 0),
                "used_bytes": int(user["used_bytes"] or 0),
                "expire_at": int(user["expire_at"] or 0),
                "max_ips": int(user["max_ips"] or 0),
                "speed_kbps": int(user["speed_kbps"] or 0),
            }
        )
    return out


@router.post("/api/node/sync")
async def node_sync(request: Request, authorization: str = Header(default=""), x_node_token: str = Header(default="")):
    location = auth_node(authorization, x_node_token)
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        payload = {}
    status = payload.get("status") or {}
    if isinstance(status, dict) and status:
        status["reported_at"] = store.now_iso()
        store.touch_location(location["id"], status)
    else:
        store.touch_location(location["id"])

    settings = store.all_settings()
    base = store.public_base()
    sub_path = settings.get("sub_path") or "sub"
    return {
        "ok": True,
        "service": "mlp",
        "panel_version": APP_VERSION,
        "server_time": int(time.time()),
        "ttl": NODE_SYNC_INTERVAL,
        "node": {
            "id": location["id"],
            "name": location["name"],
            "flag": location["flag"],
            "host": location["host"],
            "ws_path": location["ws_path"] or "/ws",
            "xhttp_path": location["xhttp_path"] or "/xhttp",
            "transports": location["transports"],
            "tcp_port": int(location["tcp_port"] or 0),
            "engine": location.get("engine") or "python",
        },
        "panel": {
            "title": settings.get("panel_title") or "MLP",
            "support_url": settings.get("support_url") or "",
            "sub_base": f"{base}/{sub_path}" if base else "",
        },
        "users": _policy_users(location),
    }


@router.post("/api/node/report")
async def node_report(request: Request, authorization: str = Header(default=""), x_node_token: str = Header(default="")):
    location = auth_node(authorization, x_node_token)
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    usage = payload.get("usage") or []
    total_delta = 0
    if isinstance(usage, list):
        users_by_uuid = {
            row["uuid"]: row["id"] for row in store.query("SELECT id, uuid FROM users")
        }
        for item in usage[:2000]:
            if not isinstance(item, dict):
                continue
            uuid = str(item.get("uuid") or "")
            user_id = users_by_uuid.get(uuid)
            if not user_id:
                continue
            total = int(item.get("total") or 0)
            total_delta += store.add_usage(int(user_id), int(location["id"]), total)

    status = payload.get("status")
    if isinstance(status, dict) and status:
        status["reported_at"] = store.now_iso()
        store.touch_location(location["id"], status)
    else:
        store.touch_location(location["id"])

    for event in (payload.get("events") or [])[:20]:
        if isinstance(event, dict):
            store.log_event(f"node:{location['name']}", str(event.get("message") or "")[:300],
                            str(event.get("level") or "info"))

    if total_delta > 0:
        store.log_event("traffic", f"{total_delta} بایت مصرف جدید از «{location['name']}» ثبت شد", "info")

    return {"ok": True, "accepted": len(usage) if isinstance(usage, list) else 0, "delta": total_delta}


@router.get("/api/node/health")
async def node_health():
    return {"ok": True, "service": "mlp", "version": APP_VERSION}


def node_env_snippet(location: dict, panel_public: str) -> str:
    """متغیرهایی که باید در سرویس نود روی Railway ست شوند."""
    base = panel_public.rstrip("/")
    return "\n".join(
        [
            f"MLP_ROLE=node",
            f"MLP_PANEL_URL={base}",
            f"MLP_NODE_TOKEN={location['token']}",
            f"MLP_NODE_NAME={location['name']}",
            f"MLP_NODE_FLAG={location['flag']}",
            f"MLP_WS_PATH={location['ws_path']}",
            f"MLP_XHTTP_PATH={location['xhttp_path']}",
        ]
    )


def verify_token(location: dict, token: str) -> bool:
    return const_time_eq(location.get("token") or "", token or "")
