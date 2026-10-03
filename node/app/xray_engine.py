"""موتور Xray-core (اختیاری) — سرعت بالاتر، مدیریت توسط همان پنل.

در این حالت:
  * خود Xray درین‌ها را روی پورت‌های داخلی می‌گیرد (WS/XHTTP)
  * nginx روی پورت عمومی، درخواست‌های مسیر پروکسی را به Xray و بقیه را به
    سایت پوششی (FastAPI) می‌فرستد
  * این ماژول کانفیگ را از باندل پنل می‌سازد، پروسه را مدیریت می‌کند و آمار
    مصرف هر کاربر را از StatsService می‌خواند و به policy می‌دهد

محدودیت‌ها نسبت به موتور پایتون: محدودیت «سرعت» و «تعداد IP هم‌زمان» روی Xray
اعمال نمی‌شود (Xray این دو را پشتیبانی نمی‌کند)؛ حجم و انقضا کامل اعمال می‌شود.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from . import settings
from .policy import policy

logger = logging.getLogger("mlp.node.xray")

XRAY_BIN = os.environ.get("MLP_XRAY_BIN", "xray")
WS_PORT = int(os.environ.get("MLP_XRAY_WS_PORT", "18080"))
XHTTP_PORT = int(os.environ.get("MLP_XRAY_XHTTP_PORT", "18081"))
API_PORT = int(os.environ.get("MLP_XRAY_API_PORT", "10085"))
STATS_INTERVAL = float(os.environ.get("MLP_XRAY_STATS_INTERVAL", "20"))
CONFIG_PATH = Path(settings.DATA_DIR) / "xray-config.json"
LOG_PATH = Path(settings.DATA_DIR) / "xray.log"


def _client_entry(user: dict) -> dict:
    return {
        "id": str(user.get("uuid")),
        "email": f"u_{user.get('uuid')}",
        "flow": "",
        "level": 0,
    }


class XrayEngine:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.available = bool(shutil.which(XRAY_BIN) or Path(XRAY_BIN).exists())
        self.transport_name = "xhttp"  # در نسخه‌های قدیمی‌تر: splithttp
        self.active_uuids: set[str] = set()
        self.last_apply = 0.0
        self.last_error = ""
        self.version = ""
        self.stats_task: asyncio.Task | None = None
        self._client = None  # اگر پکیج xray نصب باشد
        self._api = None

    # ─────────────── ساخت کانفیگ ───────────────
    def enabled_users(self) -> list[dict]:
        return [u for u in policy.users.values() if int(u.get("enabled") or 0)]

    def build_config(self) -> dict:
        clients = [_client_entry(u) for u in self.enabled_users()]
        return {
            "log": {"loglevel": os.environ.get("MLP_XRAY_LOGLEVEL", "warning"), "error": str(LOG_PATH)},
            "api": {"tag": "api", "services": ["StatsService", "HandlerService", "LoggerService"]},
            "stats": {},
            "policy": {
                "levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}},
                "system": {"statsInboundUplink": False, "statsInboundDownlink": False},
            },
            "inbounds": [
                {
                    "tag": "ws-in",
                    "listen": "127.0.0.1",
                    "port": WS_PORT,
                    "protocol": "vless",
                    "settings": {"clients": clients, "decryption": "none"},
                    "streamSettings": {
                        "network": "ws",
                        "security": "none",
                        "wsSettings": {"path": settings.WS_PATH},
                    },
                    "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": False},
                },
                {
                    "tag": "xhttp-in",
                    "listen": "127.0.0.1",
                    "port": XHTTP_PORT,
                    "protocol": "vless",
                    "settings": {"clients": clients, "decryption": "none"},
                    "streamSettings": {
                        "network": self.transport_name,
                        "security": "none",
                        self.transport_name + "Settings": {"path": settings.XHTTP_PATH, "mode": "auto"},
                    },
                    "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": False},
                },
                {
                    "tag": "api",
                    "listen": "127.0.0.1",
                    "port": API_PORT,
                    "protocol": "dokodemo-door",
                    "settings": {"address": "127.0.0.1"},
                },
            ],
            "outbounds": [
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"},
            ],
            "routing": {
                "domainStrategy": "AsIs",
                "rules": [
                    {"type": "field", "inboundTag": ["api"], "outboundTag": "api"},
                    {"type": "field", "protocol": ["bittorrent"], "outboundTag": "block"},
                ],
            },
        }

    def write_config(self) -> dict:
        config = self.build_config()
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(CONFIG_PATH)
        self.active_uuids = {str(u.get("uuid")) for u in self.enabled_users()}
        return config

    # ─────────────── پروسه ───────────────
    def check_version(self) -> str:
        if not self.available:
            return ""
        try:
            out = subprocess.run([XRAY_BIN, "version"], capture_output=True, text=True, timeout=15)
            first = (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else ""
            self.version = first.strip()
        except Exception as exc:
            self.last_error = f"version check failed: {exc}"
        return self.version

    def start(self) -> bool:
        if not self.available:
            self.last_error = f"باینری Xray پیدا نشد ({XRAY_BIN}); فقط کانفیگ نوشته می‌شود"
            self.write_config()
            policy.push_event(self.last_error, "warn")
            return False
        self.write_config()
        self.check_version()
        try:
            log = open(LOG_PATH, "ab", buffering=0)
            self.proc = subprocess.Popen(
                [XRAY_BIN, "run", "-c", str(CONFIG_PATH)],
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=str(Path(settings.DATA_DIR)),
            )
        except Exception as exc:
            self.last_error = f"اجرای Xray ناموفق: {exc}"
            policy.push_event(self.last_error, "error")
            return False
        time.sleep(1.2)
        if self.proc.poll() is not None:
            tail = ""
            with contextlib.suppress(Exception):
                tail = LOG_PATH.read_text(encoding="utf-8", errors="ignore")[-600:]
            if self.transport_name == "xhttp" and ("xhttp" in tail.lower() or "unknown transport" in tail.lower()):
                # نسخه‌های قدیمی Xray نام ترابرد را splithttp می‌دانند → یک‌بار دیگر امتحان کن
                self.transport_name = "splithttp"
                policy.push_event("ترابرد xhttp پشتیبانی نشد؛ با splithttp تلاش مجدد شد", "warn")
                return self.start()
            self.last_error = f"Xray بلافاصله بسته شد: {tail[-300:]}"
            policy.push_event(self.last_error, "error")
            return False
        policy.push_event(f"موتور Xray اجرا شد ({self.version or 'unknown version'})", "ok")
        return True

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            with contextlib.suppress(Exception):
                self.proc.terminate()
                self.proc.wait(timeout=8)
        self.proc = None

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def is_running(self) -> bool:
        return bool(self.proc and self.proc.poll() is None)

    # ─────────────── اعمال تغییرات کاربران ───────────────
    def apply(self, restart_on_change: bool = False) -> None:
        wanted = {str(u.get("uuid")) for u in self.enabled_users()}
        if wanted == self.active_uuids and self.is_running():
            return
        added = wanted - self.active_uuids
        removed = self.active_uuids - wanted
        if self.is_running() and (added or removed) and not restart_on_change:
            if self._api_users(added, removed):
                self.active_uuids = wanted
                policy.push_event(f"Xray: {len(added)} کاربر اضافه، {len(removed)} حذف (بدون ری‌استارت)", "info")
                return
        # تغییر ساختاری (مثلاً تغییر مسیرها) یا نبود API → ری‌استارت
        policy.push_event("کانفیگ Xray بازنویسی و ری‌استارت شد", "info")
        self.restart()

    def _api_users(self, added: set[str], removed: set[str]) -> bool:
        """تلاش برای افزودن/حذف کاربر از طریق HandlerService (بدون ری‌استارت)."""
        try:
            from xray import XrayClient  # type: ignore
            from xray.app.proxyman.command import command_pb2 as proxyman  # type: ignore
            from xray.common.serial import typed_message_pb2  # type: ignore
            from xray.proxy.vless.inbound import config_pb2 as vless  # type: ignore
        except Exception:
            return False
        try:
            client = XrayClient(f"127.0.0.1:{API_PORT}")
            for uuid in added:
                account = vless.Account(id=uuid, email=f"u_{uuid}")
                operation = proxyman.AddUserOperation(account=typed_message_pb2.TypedMessage(
                    type="xray.proxy.vless.inbound.Account", value=account.SerializeToString()))
                request = proxyman.AlterInboundRequest(tag="ws-in", operation=typed_message_pb2.TypedMessage(
                    type="xray.app.proxyman.command.AddUserOperation", value=operation.SerializeToString()))
                client.proxyman.AlterInbound(request)
            for uuid in removed:
                account = vless.Account(id=uuid, email=f"u_{uuid}")
                operation = proxyman.RemoveUserOperation(account=account)
                request = proxyman.AlterInboundRequest(tag="ws-in", operation=typed_message_pb2.TypedMessage(
                    type="xray.app.proxyman.command.RemoveUserOperation", value=operation.SerializeToString()))
                client.proxyman.AlterInbound(request)
            return True
        except Exception as exc:
            self.last_error = f"alter inbound failed: {exc}"
            return False

    # ─────────────── آمار ───────────────
    def _stats_via_cli(self) -> dict[str, int]:
        try:
            out = subprocess.run(
                [XRAY_BIN, "api", "statsquery", f"--server=127.0.0.1:{API_PORT}", "-pattern", "user>>>"],
                capture_output=True, text=True, timeout=15,
            )
            data = json.loads(out.stdout or "{}")
        except Exception as exc:
            self.last_error = f"statsquery failed: {exc}"
            return {}
        totals: dict[str, int] = {}
        for item in (data.get("stat") or []):
            name = item.get("name", "")
            value = int(item.get("value") or 0)
            # user>>>u_<uuid>>>>traffic>>>uplink
            parts = name.split(">>>")
            if len(parts) < 5 or parts[0] != "user":
                continue
            email = parts[1]
            uuid = email[2:] if email.startswith("u_") else email
            direction = parts[-1]
            if direction in ("uplink", "downlink"):
                totals[uuid] = totals.get(uuid, 0) + value
        return totals

    async def stats_loop(self) -> None:
        await asyncio.sleep(8)
        while True:
            try:
                if self.is_running():
                    totals = await asyncio.to_thread(self._stats_via_cli)
                    for uuid, total in totals.items():
                        policy.usage[uuid] = total
                else:
                    self.restart()
            except Exception as exc:
                logger.warning("xray stats loop error: %s", exc)
            await asyncio.sleep(STATS_INTERVAL)

    def status(self) -> dict:
        return {
            "engine": "xray",
            "available": self.available,
            "running": self.is_running(),
            "version": self.version,
            "transport": self.transport_name,
            "users": len(self.active_uuids),
            "config_path": str(CONFIG_PATH),
            "last_error": self.last_error,
            "limits_note": "محدودیت سرعت و تعداد IP در موتور Xray اعمال نمی‌شود",
        }

    def self_check(self) -> dict:
        """برای تست: کانفیگ را می‌سازد و اعتبار JSON آن را برمی‌گرداند."""
        config = self.build_config()
        text = json.dumps(config)
        inbound_tags = [i["tag"] for i in config["inbounds"]]
        return {
            "ok": bool(config["inbounds"]) and "ws-in" in inbound_tags,
            "bytes": len(text),
            "clients": len(config["inbounds"][0]["settings"]["clients"]),
            "binary_found": self.available,
            "inbounds": inbound_tags,
            "path": str(CONFIG_PATH),
            "config": config,
        }


engine = XrayEngine()
