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
    reseller_id INTEGER NOT NULL DEFAULT 0,
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
CREATE TABLE IF NOT EXISTS resellers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL DEFAULT '',
    balance INTEGER NOT NULL DEFAULT 0,
    price_gb INTEGER NOT NULL DEFAULT 0,
    price_day INTEGER NOT NULL DEFAULT 0,
    min_gb REAL NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    note TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT 0,
    last_login INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS wallet_tx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reseller_id INTEGER NOT NULL DEFAULT 0,
    amount INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL DEFAULT 'topup',
    status TEXT NOT NULL DEFAULT 'pending',
    receipt TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT 0,
    decided_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL DEFAULT 'info',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS content_blocks (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_wallet_status ON wallet_tx (status);
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
    # ── مسیر مخفی پنل و برند ──
    "secret_path": "",
    "site_mode": "marketing",          # marketing | app | countdown
    "brand_name": "آریا کلود",
    "brand_slogan": "اینترنت بدون مرز، برای همه",
    "brand_color": "#5b6cff",
    "brand_color2": "#a855f7",
    "brand_logo": "◆",
    "brand_hero": "با یک اشتراک، از هر کجا وصل شو",
    "brand_features": "چند لوکیشن\nاتصال سریع و پایدار\nپشتیبانی واقعی\nفعال‌سازی خودکار",
    "brand_card_number": "6037-XXXX-XXXX-XXXX",
    "brand_card_holder": "به نام مدیر سرویس",
    "brand_contact": "https://t.me/",
    "marketing_show_plans": "1",
    "announce_bar": "",
    "custom_domain": "",
    "xray_enabled": "0",
    "tutorial_enabled": "1",
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


def _ensure_columns() -> None:
    """مهاجرت‌های سبک: ستون‌های جدید روی پایگاه‌داده‌ی قدیمی."""
    wanted = {
        "users": {"reseller_id": "INTEGER NOT NULL DEFAULT 0"},
        "locations": {
            "engine": "TEXT NOT NULL DEFAULT 'python'",
            "decoy": "TEXT NOT NULL DEFAULT ''",
            "egress_mode": "TEXT NOT NULL DEFAULT 'direct'",
            "egress_json": "TEXT NOT NULL DEFAULT '{}'",
        },
        "plans": {"reseller_price": "INTEGER NOT NULL DEFAULT 0"},
    }
    for table, cols in wanted.items():
        existing = {row["name"] for row in query(f"PRAGMA table_info({table})")}
        for name, ddl in cols.items():
            if name not in existing:
                execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                log_event("panel", f"ستون {table}.{name} اضافه شد", "info")


def init_db() -> None:
    with _lock:
        conn = connect()
        conn.executescript(SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        _ensure_columns()
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


def location_egress(location: dict) -> dict:
    """پیکربندی مسیر خروج برای نود.

    اگر ادمین از پنل مسیر خروجی تنظیم نکرده باشد، دیکشنری خالی برمی‌گردد تا
    نود از تنظیمات env خودش (متغیرهای سرویس) استفاده کند. به‌محض اینکه در پنل
    چیزی ذخیره شود، همان اولویت دارد و زنده روی نود اعمال می‌شود.
    """
    raw = location.get("egress_json") or "{}"
    try:
        conf = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
    except Exception:
        conf = {}
    if not isinstance(conf, dict):
        conf = {}
    conf = {k: v for k, v in conf.items() if v not in (None, "", [], {})}
    if conf:
        conf["mode"] = str(conf.get("mode") or location.get("egress_mode") or "direct").lower()
    return conf


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
        "engine": str(data.get("engine") or "python").strip().lower()[:12],
        "decoy": str(data.get("decoy") or "").strip().lower()[:12],
        "egress_mode": str(data.get("egress_mode") or "direct").strip().lower()[:12],
        "egress_json": json.dumps(data.get("egress") or {}, ensure_ascii=False)[:4000],
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
def list_users(reseller_id: int | None = None) -> list[dict]:
    if reseller_id:
        users = [dict(r) for r in query("SELECT * FROM users WHERE reseller_id=? ORDER BY id DESC", (reseller_id,))]
    else:
        users = [dict(r) for r in query("SELECT * FROM users ORDER BY id DESC")]
    links: dict[int, list[int]] = {}
    for row in query("SELECT * FROM user_locations"):
        links.setdefault(row["user_id"], []).append(row["location_id"])
    names = {r["id"]: r["name"] for r in query("SELECT id, name FROM resellers")}
    for u in users:
        u["locations"] = links.get(u["id"], [])
        u["expire_iso"] = ts_to_iso(u["expire_at"])
        u["days_left"] = days_left(u["expire_at"])
        u["status"] = user_status(u)
        u["reseller_name"] = names.get(int(u.get("reseller_id") or 0), "")
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
        "reseller_id": int(data.get("reseller_id") or 0),
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
        "reseller_price": int(data.get("reseller_price") or 0),
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
    pending_top = one("SELECT COUNT(*) AS c FROM wallet_tx WHERE status='pending'")["c"]
    return {
        "users": len(users),
        "active_users": len(active),
        "locations": len(locs),
        "online_locations": len(online),
        "pending_orders": int(pending or 0),
        "pending_topups": int(pending_top or 0),
        "total_traffic": total_traffic(),
        "used_bytes": sum(int(u.get("used_bytes") or 0) for u in users),
        "limited_users": len([u for u in users if user_status(u) == "limited"]),
        "expired_users": len([u for u in users if user_status(u) == "expired"]),
    }


# ───────────────────────────── محتوا و برند ─────────────────────────────
def get_block(key: str, default: str = "") -> str:
    row = one("SELECT value FROM content_blocks WHERE key=?", (key,))
    return row["value"] if row else default


def set_block(key: str, value: str) -> None:
    execute(
        "INSERT INTO content_blocks (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value or ""),
    )


def all_blocks() -> dict[str, str]:
    return {row["key"]: row["value"] for row in query("SELECT key, value FROM content_blocks")}


def brand() -> dict:
    settings = all_settings()
    return {
        "name": settings.get("brand_name") or "سرویس من",
        "slogan": settings.get("brand_slogan") or "",
        "color": settings.get("brand_color") or "#5b6cff",
        "color2": settings.get("brand_color2") or "#a855f7",
        "logo": settings.get("brand_logo") or "◆",
        "hero": settings.get("brand_hero") or "",
        "features": [x.strip() for x in (settings.get("brand_features") or "").splitlines() if x.strip()],
        "card_number": settings.get("brand_card_number") or "",
        "card_holder": settings.get("brand_card_holder") or "",
        "contact": settings.get("brand_contact") or "",
        "plan_title": settings.get("panel_title") or "پنل",
        "site_mode": settings.get("site_mode") or "marketing",
        "announce_bar": settings.get("announce_bar") or "",
        "show_plans": settings.get("marketing_show_plans", "1") == "1",
        "custom_domain": (settings.get("custom_domain") or "").strip().rstrip("/"),
    }


def secret_path() -> str:
    raw = (get_setting("secret_path") or "").strip()
    if not raw:
        import secrets as _secrets

        raw = "/" + _secrets.token_hex(4)
        set_setting("secret_path", raw)
    raw = "/" + raw.strip("/")
    return raw


# ───────────────────────────── اعلان‌ها ─────────────────────────────
def list_announcements(only_enabled: bool = False) -> list[dict]:
    sql = "SELECT * FROM announcements"
    if only_enabled:
        sql += " WHERE enabled=1"
    sql += " ORDER BY id DESC LIMIT 50"
    return [dict(r) for r in query(sql)]


def get_announcement(aid: int) -> dict | None:
    row = one("SELECT * FROM announcements WHERE id=?", (aid,))
    return dict(row) if row else None


def save_announcement(data: dict) -> int:
    aid = int(data.get("id") or 0)
    fields = {
        "title": str(data.get("title") or "")[:120],
        "body": str(data.get("body") or "")[:2000],
        "level": str(data.get("level") or "info")[:16],
        "enabled": 1 if data.get("enabled", True) else 0,
    }
    if aid:
        sets = ", ".join(f"{k}=?" for k in fields)
        execute(f"UPDATE announcements SET {sets} WHERE id=?", (*fields.values(), aid))
        return aid
    fields["created_at"] = now_ts()
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    return int(execute(f"INSERT INTO announcements ({cols}) VALUES ({marks})", tuple(fields.values())).lastrowid)


def delete_announcement(aid: int) -> None:
    execute("DELETE FROM announcements WHERE id=?", (aid,))


def set_announce_bar(text: str) -> None:
    set_setting("announce_bar", text[:300])


# ───────────────────────────── رزیلرها ─────────────────────────────
def list_resellers() -> list[dict]:
    return [dict(r) for r in query("SELECT * FROM resellers ORDER BY id DESC")]


def get_reseller(rid: int) -> dict | None:
    row = one("SELECT * FROM resellers WHERE id=?", (rid,))
    return dict(row) if row else None


def get_reseller_by_username(username: str) -> dict | None:
    row = one("SELECT * FROM resellers WHERE username=?", (username,))
    return dict(row) if row else None


def save_reseller(data: dict) -> int:
    from .security import hash_password

    rid = int(data.get("id") or 0)
    fields = {
        "name": str(data.get("name") or "").strip()[:80],
        "username": str(data.get("username") or "").strip()[:40],
        "price_gb": int(data.get("price_gb") or 0),
        "price_day": int(data.get("price_day") or 0),
        "min_gb": float(data.get("min_gb") or 1),
        "enabled": 1 if data.get("enabled", True) else 0,
        "note": str(data.get("note") or "")[:300],
    }
    if rid:
        sets = ", ".join(f"{k}=?" for k in fields)
        execute(f"UPDATE resellers SET {sets} WHERE id=?", (*fields.values(), rid))
        if data.get("password"):
            execute("UPDATE resellers SET password_hash=? WHERE id=?", (hash_password(str(data["password"])), rid))
        return rid
    fields["username"] = fields["username"] or f"reseller{now_ts()}"
    fields["password_hash"] = hash_password(str(data.get("password") or "reseller123"))
    fields["created_at"] = now_ts()
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    return int(execute(f"INSERT INTO resellers ({cols}) VALUES ({marks})", tuple(fields.values())).lastrowid)


def delete_reseller(rid: int) -> None:
    execute("DELETE FROM resellers WHERE id=?", (rid,))
    execute("DELETE FROM wallet_tx WHERE reseller_id=?", (rid,))


def reseller_balance(rid: int) -> int:
    row = one("SELECT balance FROM resellers WHERE id=?", (rid,))
    return int(row["balance"]) if row else 0


def add_balance(rid: int, amount: int, kind: str = "topup", note: str = "", receipt: str = "",
                status: str = "approved") -> int:
    amount = int(amount)
    tx_id = int(execute(
        """INSERT INTO wallet_tx (reseller_id, amount, kind, status, receipt, note, created_at, decided_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (rid, amount, kind, status, receipt[:300], note[:300], now_ts(), now_ts() if status != "pending" else 0),
    ).lastrowid)
    if status == "approved":
        execute("UPDATE resellers SET balance = balance + ? WHERE id=?", (amount, rid))
    return tx_id


def list_wallet_tx(status: str | None = None, reseller_id: int | None = None, limit: int = 100) -> list[dict]:
    sql = "SELECT * FROM wallet_tx"
    where, params = [], []
    if status:
        where.append("status=?")
        params.append(status)
    if reseller_id:
        where.append("reseller_id=?")
        params.append(reseller_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in query(sql, params)]
    names = {r["id"]: r["name"] for r in query("SELECT id, name FROM resellers")}
    for row in rows:
        row["reseller_name"] = names.get(row["reseller_id"], "—")
    return rows


def set_tx_status(tx_id: int, status: str, note: str = "") -> dict | None:
    row = one("SELECT * FROM wallet_tx WHERE id=?", (tx_id,))
    if not row:
        return None
    tx = dict(row)
    if tx["status"] == status:
        return tx
    execute("UPDATE wallet_tx SET status=?, decided_at=?, note=? WHERE id=?", (status, now_ts(), note[:300], tx_id))
    if status == "approved" and tx["status"] != "approved":
        execute("UPDATE resellers SET balance = balance + ? WHERE id=?", (int(tx["amount"]), int(tx["reseller_id"])))
    if status == "rejected" and tx["status"] == "approved":
        execute("UPDATE resellers SET balance = balance - ? WHERE id=?", (int(tx["amount"]), int(tx["reseller_id"])))
    return get_tx(tx_id)


def get_tx(tx_id: int) -> dict | None:
    row = one("SELECT * FROM wallet_tx WHERE id=?", (tx_id,))
    return dict(row) if row else None


def charge_reseller(rid: int, amount: int, note: str = "") -> bool:
    """کسر از کیف پول رزیلر (اگر موجودی کافی باشد)."""
    amount = int(amount)
    if amount <= 0:
        return True
    if reseller_balance(rid) < amount:
        return False
    add_balance(rid, -amount, kind="purchase", note=note, status="approved")
    return True


def reseller_user_summary(rid: int) -> dict:
    users = [dict(r) for r in query("SELECT * FROM users WHERE reseller_id=?", (rid,))]
    return {
        "users": len(users),
        "used": sum(int(u.get("used_bytes") or 0) for u in users),
        "active": len([u for u in users if user_status(u) == "active"]),
    }
