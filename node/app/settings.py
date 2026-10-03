"""تنظیمات سرویس نود."""

from __future__ import annotations

import os
from pathlib import Path

APP_VERSION = "1.0.0"

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
