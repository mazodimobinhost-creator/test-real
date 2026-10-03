"""تنظیمات و اطلاعات پایه‌ی پنل مرکزی (Multi-Location Panel)."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "MLP"
APP_VERSION = "1.0.0"
APP_TITLE_FA = "پنل مولتی‌لوکیشن"

# مسیر داده: روی Railway باید یک Volume به همین مسیر وصل شود
DATA_DIR = Path(os.environ.get("MLP_DATA_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or "/data")
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    DATA_DIR = Path("./data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "mlp.sqlite3"

# رمز اولیه‌ی ادمین (فقط بار اول استفاده می‌شود؛ بعد از تغییر در پنل ذخیره می‌شود)
DEFAULT_ADMIN_USER = os.environ.get("MLP_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("MLP_ADMIN_PASSWORD", "admin")

# دامنه‌ی عمومی پنل (Railway خودش تزریق می‌کند)
PUBLIC_BASE_URL = (os.environ.get("MLP_PUBLIC_URL") or "").strip().rstrip("/")
if not PUBLIC_BASE_URL:
    dom = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    PUBLIC_BASE_URL = f"https://{dom}" if dom else ""

PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")

# مسیر لینک اشتراک
SUB_PATH = os.environ.get("MLP_SUB_PATH", "sub").strip("/") or "sub"

# بازه‌ی پیشنهادی به نودها برای sync (ثانیه)
NODE_SYNC_INTERVAL = int(os.environ.get("MLP_NODE_SYNC_INTERVAL", "15"))
# اگر نودی بیشتر از این مدت خبر نده، آفلاین در نظر گرفته می‌شود
NODE_OFFLINE_AFTER = int(os.environ.get("MLP_NODE_OFFLINE_AFTER", "90"))
