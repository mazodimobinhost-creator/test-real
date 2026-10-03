#!/usr/bin/env python3
"""فایل‌های راه‌اندازی را برای دکمه‌های «دانلود» داخل پنل بسته‌بندی می‌کند.

چون ایمیج پنل فقط پوشه‌ی panel/ را کپی می‌کند، محتوای فایل‌های دیگر بخش‌های
مخزن (نود، ورکر) را در panel/setup_files.json جمع می‌کنیم. CI بررسی می‌کند که
این فایل با مخزن هم‌خوان باشد.

    python3 tools/gen_setup_files.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = [
    "panel/Dockerfile",
    "panel/railway.toml",
    "panel/requirements.txt",
    "panel/.env.example",
    "node/Dockerfile",
    "node/Dockerfile.xray",
    "node/nginx.conf.template",
    "node/start-xray.sh",
    "node/install-vps.sh",
    "node/railway.toml",
    "node/.env.example",
    "worker/worker.js",
]


def build() -> dict:
    out: dict[str, str] = {}
    for rel in FILES:
        path = ROOT / rel
        if path.exists():
            out[rel] = path.read_text(encoding="utf-8")
    return out


def main() -> int:
    payload = build()
    target = ROOT / "panel" / "setup_files.json"
    text = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True)
    if "--check" in sys.argv:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current.strip() != text.strip():
            print("setup_files.json با مخزن هم‌خوان نیست؛ اجرا کن: python3 tools/gen_setup_files.py", file=sys.stderr)
            return 1
        print("setup_files.json هم‌خوان است ✓")
        return 0
    target.write_text(text, encoding="utf-8")
    print(f"نوشته شد: {target} ({len(payload)} فایل، {len(text)} بایت)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
