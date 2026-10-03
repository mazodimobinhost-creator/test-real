"""لایه‌ی داده‌ی پنل روی SQLite (بدون ORM، ساده و سریع)."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from . import settings
from .security import hash_password, new_token, new_uuid, now_ts

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    flag TEXT NOT NULL DEFAULT '🌍',
    region TEXT NOT NULL DEFAULT '',
    host TEXT NOT NULL DEFAULT '',
    token TEXT NOT NULL DEFAULT '',
    transports TEXT NOT NULL DEFAULT '["ws"]',
    ws_path TEXT NOT NULL DEFAULT '/ws',
    xhttp_path TEXT NOT NULL DEFAULT '/xhttp',
    tcp_port INTEGER NOT NULL DEFAULT 0,
    cf_host TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    last_seen INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    uuid TEXT NOT NULL UNIQUE,
    sub_token TEXT NOT NULL UNIQUE,
    limit_bytes INTEGER NOT NULL DEFAULT 0,
    used_bytes INTEGER NOT NULL DEFAULT 0,
    expire_at INTEGER NOT NULL DEFAULT 0,
    max_ips INTEGER NOT NULL DEFAULT 0,
    speed_kbps INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    note TEXT NOT NULL DEFAULT '',
    telegram_id TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS user_locations (
    user_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, location_id)
);
CREATE TABLE IF NOT EXISTS usage_marks (
    user_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    last_total INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, location_id)
);
CREATE TABLE IF NOT EXISTS traffic_hourly (hour TEXT PRIMARY KEY, bytes INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    days INTEGER NOT NULL DEFAULT 30,
    traffic_gb REAL NOT NULL DEFAULT 0,
    price TEXT NOT NULL DEFAULT '',
    max_ips INTEGER NOT NULL DEFAULT 0,
    speed_kbps INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT NOT NULL DEFAULT '',
    who TEXT NOT NULL DEFAULT '',
    plan_id INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    receipt TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT 0,
    decided_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL DEFAULT 0,
    level TEXT NOT NULL DEFAULT 'info',
    kind TEXT NOT NULL DEFAULT 'general',
    message TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sessions (
    sid TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL DEFAULT 0,
    expires_at INTEGER NOT NULL DEFAULT 0,
    ip TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
"""

DEFAULT_SETTINGS: dict[str, str] = {
    "panel_title": "پنل مولتی‌لوکیشن",
    "sub_title": "لینک اشتراک شما",
    "support_url": "https://t.me/",
    "public_base_url": "",
    "sub_path": settings.SUB_PATH,
    "admin_user": settings.DEFAULT_ADMIN_USER,
    "admin_password_hash": "",
    "bot_token": "",
    "bot_enabled": "0",
    "bot_admin_ids": "",
    "bot_force_channel": "",
    "bot_sales_enabled": "1",
    "bot_text_start": "سلام 👋\nبه {panel} خوش آمدید.\nبرای دیدن سرویس خود /me و برای خرید /plans را بزنید.",
    "node_default_ws_path": "/ws",
    "node_default_xhttp_path": "/xhttp",
    "traffic_multiplier": "1",
    "first_run_done": "0",
}


# ───────────────────────────── ابزارهای پایه ─────────────────────────────────
def connect() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False, timeout=30)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA synchronous=NORMAL")
            _conn.execute("PRAGMA foreign_keys=ON")
        return _conn


def init_db() -> None:
    with _lock:
        conn = connect()
        conn.executescript(SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        cur = conn.execute("SELECT value FROM settings WHERE key='admin_password_hash'")
        row = cur.fetchone()
        if not row or not row["value"]:
            set_setting("admin_password_hash", hash_password(settings.DEFAULT_ADMIN_PASSWORD))
        set_setting("first_run_done", "1")


def query(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with _lock:
        return list(connect().execute(sql, tuple(params)).fetchall())


def one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with _lock:
        return connect().execute(sql, tuple(params)).fetchone()


def execute(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    with _lock:
        conn = connect()
        cur = conn.execute(sql, tuple(params))
        conn.commit()
        return cur


# ───────────────────────────── تنظیمات ───────────────────────────────────────
def get_setting(key: str, default: str = "") -> str:
    row = one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def all_settings() -> dict[str, str]:
    out = dict(DEFAULT_SETTINGS)
    for row in query("SELECT key, value FROM settings"):
        out[row["key"]] = row["value"]
    return out


def public_base() -> str:
    base = (get_setting("public_base_url") or settings.PUBLIC_BASE_URL or "").strip().rstrip("/")
    return base


# ───────────────────────────── زمان ─────────────────────────────────────────
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def days_from_now_ts(days: int) -> int:
    if days <= 0:
        return 0
    return int(time.time()) + days * 86400


def ts_to_iso(ts: int) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def days_left(expire_ts: int) -> int | None:
    if not expire_ts:
        return None
    return max(0, int((expire_ts - time.time()) // 86400))


# ───────────────────────────── رویدادها ─────────────────────────────────────
def log_event(kind: str, message: str, level: str = "info") -> None:
    execute("INSERT INTO events (ts, level, kind, message) VALUES (?,?,?,?)", (now_ts(), level, kind, message[:900]))
    # نگه‌داشتن حداکثر ۵۰۰ رویداد آخر
    execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 500)")


def list_events(limit: int = 100) -> list[dict]:
    return [dict(r) for r in query("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]


def clear_events() -> None:
    execute("DELETE FROM events")


# ───────────────────────────── لوکیشن‌ها ────────────────────────────────────
def _location_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["transports"] = json.loads(d.get("transports") or "[]") or ["ws"]
    except Exception:
        d["transports"] = ["ws"]
    try:
        d["status"] = json.loads(d.get("status") or "{}")
    except Exception:
        d["status"] = {}
    return d


def list_locations(only_enabled: bool = False) -> list[dict]:
    sql = "SELECT * FROM locations"
    if only_enabled:
        sql += " WHERE enabled=1"
    sql += " ORDER BY sort ASC, id ASC"
    return [_location_row(r) for r in query(sql)]


def get_location(loc_id: int) -> dict | None:
    row = one("SELECT * FROM locations WHERE id=?", (loc_id,))
    return _location_row(row) if row else None


def get_location_by_token(token: str) -> dict | None:
    if not token:
        return None
    row = one("SELECT * FROM locations WHERE token=?", (token,))
    return _location_row(row) if row else None


def save_location(data: dict) -> int:
    loc_id = int(data.get("id") or 0)
    fields = {
        "name": str(data.get("name") or "").strip()[:80],
        "flag": str(data.get("flag") or "🌍").strip()[:8],
        "region": str(data.get("region") or "").strip()[:40],
        "host": str(data.get("host") or "").strip().rstrip("/")[:200],
        "transports": json.dumps(data.get("transports") or ["ws"]),
        "ws_path": str(data.get("ws_path") or "/ws").strip()[:80],
        "xhttp_path": str(data.get("xhttp_path") or "/xhttp").strip()[:80],
        "tcp_port": int(data.get("tcp_port") or 0),
        "cf_host": str(data.get("cf_host") or "").strip()[:200],
        "enabled": 1 if data.get("enabled", True) else 0,
        "sort": int(data.get("sort") or 0),
        "note": str(data.get("note") or "")[:400],
    }
    if loc_id:
        sets = ", ".join(f"{k}=?" for k in fields)
        execute(f"UPDATE locations SET {sets} WHERE id=?", (*fields.values(), loc_id))
        return loc_id
    fields["token"] = new_token("mlp_")
    fields["created_at"] = now_ts()
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    cur = execute(f"INSERT INTO locations ({cols}) VALUES ({marks})", tuple(fields.values()))
    return int(cur.lastrowid)


def rotate_location_token(loc_id: int) -> str:
    token = new_token("mlp_")
    execute("UPDATE locations SET token=? WHERE id=?", (token, loc_id))
    return token


def delete_location(loc_id: int) -> None:
    execute("DELETE FROM locations WHERE id=?", (loc_id,))
    execute("DELETE FROM user_locations WHERE location_id=?", (loc_id,))
    execute("DELETE FROM usage_marks WHERE location_id=?", (loc_id,))


def touch_location(loc_id: int, status: dict | None = None) -> None:
    if status is None:
        execute("UPDATE locations SET last_seen=? WHERE id=?", (now_ts(), loc_id))
        return
    execute(
        "UPDATE locations SET last_seen=?, status=? WHERE id=?",
        (now_ts(), json.dumps(status), loc_id),
    )


def location_is_online(loc: dict) -> bool:
    return bool(loc.get("last_seen")) and (now_ts() - int(loc["last_seen"]) <= settings.NODE_OFFLINE_AFTER)


# ───────────────────────────── کاربران ─────────────────────────────────────
def list_users() -> list[dict]:
    users = [dict(r) for r in query("SELECT * FROM users ORDER BY id DESC")]
    marks = {r["user_id"]: r for r in query("SELECT * FROM usage_marks")}
    links: dict[int, list[int]] = {}
    for row in query("SELECT * FROM user_locations"):
        links.setdefault(row["user_id"], []).append(row["location_id"])
    for u in users:
        u["locations"] = links.get(u["id"], [])
        u["expire_iso"] = ts_to_iso(u["expire_at"])
        u["days_left"] = days_left(u["expire_at"])
        u["status"] = user_status(u)
        u.setdefault("_", None)
    return users


def get_user(user_id: int) -> dict | None:
    row = one("SELECT * FROM users WHERE id=?", (user_id,))
    return dict(row) if row else None


def get_user_by_sub(token: str) -> dict | None:
    row = one("SELECT * FROM users WHERE sub_token=?", (token,))
    return dict(row) if row else None


def get_user_by_telegram(tg_id: str) -> dict | None:
    row = one("SELECT * FROM users WHERE telegram_id=? ORDER BY id DESC LIMIT 1", (str(tg_id),))
    return dict(row) if row else None


def user_status(user: dict) -> str:
    if not user:
        return "unknown"
    if not int(user.get("enabled", 1)):
        return "disabled"
    expire = int(user.get("expire_at") or 0)
    if expire and expire <= now_ts():
        return "expired"
    limit = int(user.get("limit_bytes") or 0)
    if limit and int(user.get("used_bytes") or 0) >= limit:
        return "limited"
    return "active"


def save_user(data: dict) -> int:
    user_id = int(data.get("id") or 0)
    fields = {
        "name": str(data.get("name") or "").strip()[:80],
        "limit_bytes": int(data.get("limit_bytes") or 0),
        "expire_at": int(data.get("expire_at") or 0),
        "max_ips": int(data.get("max_ips") or 0),
        "speed_kbps": int(data.get("speed_kbps") or 0),
        "enabled": 1 if data.get("enabled", True) else 0,
        "note": str(data.get("note") or "")[:400],
        "telegram_id": str(data.get("telegram_id") or "").strip()[:32],
    }
    if user_id:
        sets = ", ".join(f"{k}=?" for k in fields)
        execute(f"UPDATE users SET {sets} WHERE id=?", (*fields.values(), user_id))
    else:
        fields["uuid"] = new_uuid()
        fields["sub_token"] = new_token("", 18)
        fields["created_at"] = now_ts()
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        cur = execute(f"INSERT INTO users ({cols}) VALUES ({marks})", tuple(fields.values()))
        user_id = int(cur.lastrowid)
    locs = data.get("locations")
    if locs is not None:
        set_user_locations(user_id, [int(x) for x in locs])
    return user_id


def set_user_locations(user_id: int, location_ids: list[int]) -> None:
    execute("DELETE FROM user_locations WHERE user_id=?", (user_id,))
    for loc_id in location_ids:
        execute(
            "INSERT OR REPLACE INTO user_locations (user_id, location_id, enabled) VALUES (?,?,1)",
            (user_id, int(loc_id)),
        )
        execute(
            "INSERT OR IGNORE INTO usage_marks (user_id, location_id, last_total) VALUES (?,?,0)",
            (user_id, int(loc_id)),
        )


def enabled_locations_for_user(user_id: int) -> list[dict]:
    rows = query(
        """SELECT l.* FROM locations l
           JOIN user_locations ul ON ul.location_id = l.id
           WHERE ul.user_id=? AND ul.enabled=1 AND l.enabled=1
           ORDER BY l.sort ASC, l.id ASC""",
        (user_id,),
    )
    return [_location_row(r) for r in rows]


def delete_user(user_id: int) -> None:
    execute("DELETE FROM users WHERE id=?", (user_id,))
    execute("DELETE FROM user_locations WHERE user_id=?", (user_id,))
    execute("DELETE FROM usage_marks WHERE user_id=?", (user_id,))


def reset_user_usage(user_id: int) -> None:
    execute("UPDATE users SET used_bytes=0 WHERE id=?", (user_id,))


def sync_user_locations_all() -> None:
    """هر کاربر را روی همه‌ی لوکیشن‌ها فعال می‌کند (زمانی که لوکیشن جدید ساخته می‌شود)."""
    for user in query("SELECT id FROM users"):
        for loc in query("SELECT id FROM locations WHERE enabled=1"):
            execute(
                "INSERT OR IGNORE INTO user_locations (user_id, location_id, enabled) VALUES (?,?,1)",
                (user["id"], loc["id"]),
            )


def enable_user_on_all_locations(user_id: int) -> None:
    for loc in query("SELECT id FROM locations WHERE enabled=1"):
        execute(
            "INSERT OR IGNORE INTO user_locations (user_id, location_id, enabled) VALUES (?,?,1)",
            (user_id, loc["id"]),
        )


# ───────────────────────────── مصرف ────────────────────────────────────────
def add_usage(user_id: int, location_id: int, total_bytes: int) -> int:
    """total_bytes = شمارنده‌ی تجمعی نود. دلتا محاسبه و ذخیره می‌شود.

    اگر شمارنده کوچک‌تر از قبل باشد یعنی نود ری‌استارت شده → دلتا = مقدار جدید.
    """
    total_bytes = max(0, int(total_bytes))
    row = one("SELECT last_total FROM usage_marks WHERE user_id=? AND location_id=?", (user_id, location_id))
    last = int(row["last_total"]) if row else 0
    delta = total_bytes - last if total_bytes >= last else total_bytes
    if delta <= 0:
        if row is None:
            execute(
                "INSERT OR REPLACE INTO usage_marks (user_id, location_id, last_total) VALUES (?,?,?)",
                (user_id, location_id, total_bytes),
            )
        return 0
    execute(
        "INSERT OR REPLACE INTO usage_marks (user_id, location_id, last_total) VALUES (?,?,?)",
        (user_id, location_id, total_bytes),
    )
    execute("UPDATE users SET used_bytes = used_bytes + ? WHERE id=?", (delta, user_id))
    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    execute(
        "INSERT INTO traffic_hourly (hour, bytes) VALUES (?, ?) ON CONFLICT(hour) DO UPDATE SET bytes = bytes + ?",
        (hour, delta, delta),
    )
    return delta


def hourly_traffic(hours: int = 24) -> list[dict]:
    rows = query("SELECT hour, bytes FROM traffic_hourly ORDER BY hour DESC LIMIT ?", (hours,))
    return [dict(r) for r in reversed(rows)]


def total_traffic() -> int:
    row = one("SELECT COALESCE(SUM(bytes),0) AS s FROM traffic_hourly")
    return int(row["s"]) if row else 0


def user_usage_days(user_id: int) -> dict:
    """حجم مصرفی امروز (بر اساس ترافیک کل، تقریبی)."""
    return {"total": int((get_user(user_id) or {}).get("used_bytes") or 0)}


# ───────────────────────────── پلن‌ها ──────────────────────────────────────
def list_plans(only_enabled: bool = False) -> list[dict]:
    sql = "SELECT * FROM plans"
    if only_enabled:
        sql += " WHERE enabled=1"
    sql += " ORDER BY sort ASC, id ASC"
    return [dict(r) for r in query(sql)]


def get_plan(plan_id: int) -> dict | None:
    row = one("SELECT * FROM plans WHERE id=?", (plan_id,))
    return dict(row) if row else None


def save_plan(data: dict) -> int:
    plan_id = int(data.get("id") or 0)
    fields = {
        "name": str(data.get("name") or "").strip()[:80],
        "days": int(data.get("days") or 0),
        "traffic_gb": float(data.get("traffic_gb") or 0),
        "price": str(data.get("price") or "")[:60],
        "max_ips": int(data.get("max_ips") or 0),
        "speed_kbps": int(data.get("speed_kbps") or 0),
        "enabled": 1 if data.get("enabled", True) else 0,
        "sort": int(data.get("sort") or 0),
    }
    if plan_id:
        sets = ", ".join(f"{k}=?" for k in fields)
        execute(f"UPDATE plans SET {sets} WHERE id=?", (*fields.values(), plan_id))
        return plan_id
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    cur = execute(f"INSERT INTO plans ({cols}) VALUES ({marks})", tuple(fields.values()))
    return int(cur.lastrowid)


def delete_plan(plan_id: int) -> None:
    execute("DELETE FROM plans WHERE id=?", (plan_id,))


# ───────────────────────────── سفارش‌ها ────────────────────────────────────
def list_orders(status: str | None = None, limit: int = 100) -> list[dict]:
    if status:
        rows = query("SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit))
    else:
        rows = query("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
    out = []
    plans = {p["id"]: p for p in list_plans()}
    for row in rows:
        d = dict(row)
        d["plan"] = plans.get(d["plan_id"], {})
        out.append(d)
    return out


def get_order(order_id: int) -> dict | None:
    row = one("SELECT * FROM orders WHERE id=?", (order_id,))
    return dict(row) if row else None


def create_order(telegram_id: str, who: str, plan_id: int, receipt: str = "", note: str = "") -> int:
    cur = execute(
        """INSERT INTO orders (telegram_id, who, plan_id, status, receipt, note, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (str(telegram_id), who[:80], int(plan_id), "pending", receipt[:300], note[:300], now_ts()),
    )
    return int(cur.lastrowid)


def set_order_status(order_id: int, status: str, note: str = "") -> None:
    execute("UPDATE orders SET status=?, decided_at=?, note=? WHERE id=?", (status, now_ts(), note[:300], order_id))


# ───────────────────────────── نشست‌ها ─────────────────────────────────────
def create_session(ip: str = "", ttl: int = 7 * 86400) -> str:
    sid = new_token("s_", 24)
    execute(
        "INSERT INTO sessions (sid, created_at, expires_at, ip) VALUES (?,?,?,?)",
        (sid, now_ts(), now_ts() + ttl, ip[:60]),
    )
    return sid


def get_session(sid: str) -> dict | None:
    row = one("SELECT * FROM sessions WHERE sid=?", (sid,))
    if not row:
        return None
    if row["expires_at"] < now_ts():
        execute("DELETE FROM sessions WHERE sid=?", (sid,))
        return None
    return dict(row)


def delete_session(sid: str) -> None:
    execute("DELETE FROM sessions WHERE sid=?", (sid,))


def stats_overview() -> dict:
    users = [dict(r) for r in query("SELECT * FROM users")]
    active = [u for u in users if user_status(u) == "active"]
    locs = list_locations()
    online = [l for l in locs if location_is_online(l)]
    pending = one("SELECT COUNT(*) AS c FROM orders WHERE status='pending'")["c"]
    return {
        "users": len(users),
        "active_users": len(active),
        "locations": len(locs),
        "online_locations": len(online),
        "pending_orders": int(pending or 0),
        "total_traffic": total_traffic(),
        "used_bytes": sum(int(u.get("used_bytes") or 0) for u in users),
        "limited_users": len([u for u in users if user_status(u) == "limited"]),
        "expired_users": len([u for u in users if user_status(u) == "expired"]),
    }
