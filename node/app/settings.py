"""تنظیمات سرویس نود."""

from __future__ import annotations

import os
from pathlib import Path

APP_VERSION = "1.0.0"

# موتور دیتاپلین: python (پیش‌فرض، اعمال کامل محدودیت‌ها) یا xray (سرعت بالاتر)
ENGINE = (os.environ.get("MLP_ENGINE") or "python").strip().lower()

PANEL_URL = (os.environ.get("MLP_PANEL_URL") or "").strip().rstrip("/")
NODE_TOKEN = (os.environ.get("MLP_NODE_TOKEN") or "").strip()
NODE_NAME = os.environ.get("MLP_NODE_NAME", "node")
NODE_FLAG = os.environ.get("MLP_NODE_FLAG", "🌍")

WS_PATH = "/" + (os.environ.get("MLP_WS_PATH", "/ws").strip("/") or "ws")
XHTTP_PATH = "/" + (os.environ.get("MLP_XHTTP_PATH", "/xhttp").strip("/") or "xhttp")
TCP_PORT = int(os.environ.get("MLP_TCP_PORT", "0"))

SYNC_INTERVAL = float(os.environ.get("MLP_SYNC_INTERVAL", "15"))
REPORT_INTERVAL = float(os.environ.get("MLP_REPORT_INTERVAL", "15"))

DATA_DIR = Path(os.environ.get("MLP_NODE_DATA_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or "/tmp/mlp-node")
DATA_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")

# محدودیت‌ها
MAX_BODY = int(os.environ.get("MLP_MAX_BODY", str(8 * 1024 * 1024)))
IP_WINDOW_SECONDS = int(os.environ.get("MLP_IP_WINDOW", "120"))
SESSION_IDLE_TIMEOUT = float(os.environ.get("MLP_XHTTP_IDLE", "45"))
CONNECT_TIMEOUT = float(os.environ.get("MLP_CONNECT_TIMEOUT", "12"))
# اگر باندل پنل قدیمی‌تر از این مقدار باشد، کاربران فعلی معتبر می‌مانند (پنل قطع = قطع نشدن کاربر)
ALLOW_STALE_BUNDLE_SECONDS = float(os.environ.get("MLP_ALLOW_STALE_BUNDLE", "3600"))

# سایت پوششی (Decoy): auto | shop | corp | blog | none
DECOY = (os.environ.get("MLP_DECOY") or "auto").strip().lower()
DECOY_NAME = os.environ.get("MLP_DECOY_NAME", "").strip()

# در موتور Xray، این پورت داخلی است که nginx ترافیک غیرپروکسی را به آن می‌دهد
INTERNAL_PORT = int(os.environ.get("MLP_INTERNAL_PORT", "8090"))

# ── مسیر خروج (Egress) ──
# direct | proxy | chain | auto   ·   auto = اول مسیر تنظیم‌شده، در خرابی مسیر سالم بعدی
EGRESS = (os.environ.get("MLP_EGRESS") or "direct").strip().lower()
EGRESS_FALLBACK = (os.environ.get("MLP_EGRESS_FALLBACK") or "1").strip() not in ("0", "false", "no")
EGRESS_TEST_TARGET = (os.environ.get("MLP_EGRESS_TEST_TARGET") or "1.1.1.1:443").strip()
EGRESS_PROBE = float(os.environ.get("MLP_EGRESS_PROBE", "0"))

# پروکسی IP (SOCKS5 / SOCKS5h / HTTP CONNECT) — می‌تواند چندتایی باشد
PROXY_TYPE = (os.environ.get("MLP_PROXY_TYPE") or os.environ.get("MLP_PROXY_PROTOCOL") or "socks5h").strip().lower()
PROXY_HOST = (os.environ.get("MLP_PROXY_IP") or os.environ.get("MLP_PROXY_HOST") or "").strip()
PROXY_PORT = int(os.environ.get("MLP_PROXY_PORT") or 1080)
PROXY_USER = os.environ.get("MLP_PROXY_USER", "")
PROXY_PASS = os.environ.get("MLP_PROXY_PASS", "")
PROXY_ROTATE = (os.environ.get("MLP_PROXY_ROTATE") or "fastest").strip().lower()
PROXY_LIST = [
    line.strip()
    for line in (os.environ.get("MLP_PROXY_LIST") or "").replace(",", "\n").splitlines()
    if line.strip()
]

# تانل/چین VLESS: خروج از طریق یک سرور بالادستی
CHAIN_HOST = (os.environ.get("MLP_CHAIN_HOST") or "").strip()
CHAIN_PORT = int(os.environ.get("MLP_CHAIN_PORT") or 443)
CHAIN_PATH = (os.environ.get("MLP_CHAIN_PATH") or "/ws").strip()
CHAIN_UUID = (os.environ.get("MLP_CHAIN_UUID") or "").strip()
CHAIN_TLS = (os.environ.get("MLP_CHAIN_TLS") or "1").strip() not in ("0", "false", "no")
CHAIN_SNI = (os.environ.get("MLP_CHAIN_SNI") or "").strip()
CHAIN_INSECURE = (os.environ.get("MLP_CHAIN_INSECURE") or "0").strip() in ("1", "true", "yes")
# آدرس سوئیچ ورکر Cloudflare/تانل آماده (برای مستندسازی و اسنیپت‌ها)
CHAIN_LABEL = (os.environ.get("MLP_CHAIN_LABEL") or "").strip()


def chain_config() -> dict:
    return {
        "host": CHAIN_HOST,
        "port": CHAIN_PORT,
        "path": CHAIN_PATH,
        "uuid": CHAIN_UUID,
        "tls": CHAIN_TLS,
        "sni": CHAIN_SNI,
        "insecure": CHAIN_INSECURE,
    }


# ── تشخیص IP و موقعیت (برای نمایش در پنل) ──
GEO_ENABLED = (os.environ.get("MLP_GEO_ENABLED") or "1").strip() not in ("0", "false", "no")
GEO_INTERVAL = float(os.environ.get("MLP_GEO_INTERVAL", "900"))
GEO_URL = (os.environ.get("MLP_GEO_URL") or "").strip()      # آدرس سفارشی (برای تست/سرویس داخلی)

# ── محافظت (ضد بن/سوءاستفاده) ──
BLOCK_PORTS = {
    int(x)
    for x in (os.environ.get("MLP_BLOCK_PORTS") or "25,465,587,6667,6697,137,138,139,445,1900,11211").replace(" ", "").split(",")
    if x.strip().isdigit()
}
MAX_CONN_PER_IP_MIN = int(os.environ.get("MLP_MAX_CONN_PER_IP_MIN", "90"))
MAX_CONN = int(os.environ.get("MLP_MAX_CONN", "1200"))
PROBE_BAN_AFTER = int(os.environ.get("MLP_PROBE_BAN_AFTER", "40"))
BAN_SECONDS = int(os.environ.get("MLP_BAN_SECONDS", "600"))

# ── اسکنر ──
SCAN_TIMEOUT = float(os.environ.get("MLP_SCAN_TIMEOUT", "3"))
SCAN_ATTEMPTS = int(os.environ.get("MLP_SCAN_ATTEMPTS", "3"))

# بهینه‌سازی: اندازه‌ی بافر خواندن و آستانه‌ی درین تطبیقی
READ_BUFFER = int(os.environ.get("MLP_READ_BUFFER", str(128 * 1024)))
DRAIN_HIGH_WATER = int(os.environ.get("MLP_DRAIN_HIGH_WATER", str(2 * 1024 * 1024)))
