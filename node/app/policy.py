"""سیاست‌ها روی نود: احراز کاربر، کوتا، محدودیت سرعت و IP."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from . import settings

MIN_RATE = 1024
MIN_BURST = 32 * 1024


class Bucket:
    """سطل توکن برای محدودیت سرعت هر کاربر (نرخ بر حسب بایت بر ثانیه)."""

    __slots__ = ("rate", "capacity", "tokens", "last")

    def __init__(self, rate: float) -> None:
        self.rate = max(rate, MIN_RATE)
        self.capacity = max(self.rate, MIN_BURST)
        self.tokens = self.capacity
        self.last = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last
        if elapsed > 0:
            self.last = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

    async def _wait_for(self, nbytes: int) -> None:
        while True:
            self._refill()
            if self.tokens >= nbytes:
                self.tokens -= nbytes
                return
            deficit = nbytes - self.tokens
            await asyncio.sleep(min(max(deficit / self.rate, 0.004), 0.5))

    async def consume(self, nbytes: int) -> None:
        """چانک‌های بزرگ‌تر از ظرفیت سطل را به قطعات قابل‌عبور می‌شکند (وگرنه قفل می‌شد)."""
        nbytes = int(nbytes)
        while nbytes > 0:
            take = min(nbytes, int(self.capacity))
            if take <= 0:
                return
            await self._wait_for(take)
            nbytes -= take


def _egress_summary() -> str:
    """خلاصه‌ی مسیر خروج برای گزارش به پنل (بدون import چرخه‌ای)."""
    try:
        from .egress import egress

        label = egress.active or (egress.paths[0].label if egress.paths else "مستقیم")
        return f"{egress.mode}:{label}"
    except Exception:
        return "direct"


class Policy:
    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.usage: dict[str, int] = {}
        self.ips: dict[str, dict[str, float]] = {}
        self.buckets: dict[str, Bucket] = {}
        self.connections: dict[str, float] = {}
        self.bundle_version = 0
        self.bundle_at = 0.0
        self.node_meta: dict[str, Any] = {}
        self.panel_meta: dict[str, Any] = {}
        self.lock = asyncio.Lock()
        self.started_at = time.time()
        self.total_requests = 0
        self.errors = 0
        self.active_conns = 0
        self.events: list[dict] = []

    # ── باندل ──
    def apply_bundle(self, bundle: dict) -> None:
        users = {}
        for item in bundle.get("users") or []:
            uuid = str(item.get("uuid") or "")
            if uuid:
                users[uuid] = item
        self.users = users
        self.node_meta = bundle.get("node") or {}
        self.panel_meta = bundle.get("panel") or {}
        self.bundle_version += 1
        self.bundle_at = time.time()
        for uuid in list(self.usage):
            if uuid not in users:
                self.usage.pop(uuid, None)
                self.ips.pop(uuid, None)
                self.connections.pop(uuid, None)

    def stale_bundle(self) -> bool:
        if not self.bundle_at:
            return True
        return (time.time() - self.bundle_at) > settings.ALLOW_STALE_BUNDLE_SECONDS

    # ── احراز و کوتا ──
    def _user(self, uuid: str) -> dict | None:
        return self.users.get(uuid)

    def allow(self, uuid: str) -> tuple[bool, str]:
        user = self._user(uuid)
        if not user:
            return False, "unknown"
        if not int(user.get("enabled") or 0):
            return False, str(user.get("status") or "disabled")
        expire = int(user.get("expire_at") or 0)
        if expire and expire <= int(time.time()):
            return False, "expired"
        limit = int(user.get("limit_bytes") or 0)
        if limit and (int(user.get("used_bytes") or 0) + self.usage.get(uuid, 0)) >= limit:
            return False, "limited"
        return True, "ok"

    def note(self, uuid: str, nbytes: int) -> None:
        if nbytes > 0:
            self.usage[uuid] = self.usage.get(uuid, 0) + nbytes
        self.connections[uuid] = time.time()

    def used_local(self, uuid: str) -> int:
        return self.usage.get(uuid, 0)

    # ── محدودیت IP ──
    def check_ip(self, uuid: str, ip: str) -> bool:
        user = self._user(uuid)
        if not user:
            return False
        max_ips = int(user.get("max_ips") or 0)
        if not max_ips:
            return True
        now = time.time()
        records = self.ips.setdefault(uuid, {})
        for key, seen in list(records.items()):
            if now - seen > settings.IP_WINDOW_SECONDS:
                records.pop(key, None)
        records[ip] = now
        return len(records) <= max_ips

    # ── سرعت ──
    async def throttle(self, uuid: str, nbytes: int) -> None:
        user = self._user(uuid)
        if not user or nbytes <= 0:
            return
        kbps = int(user.get("speed_kbps") or 0)
        if kbps <= 0:
            return
        rate = kbps * 1024 / 8  # kbps → bytes/sec
        bucket = self.buckets.get(uuid)
        if bucket is None or abs(bucket.rate - max(rate, MIN_RATE)) > 1:
            bucket = Bucket(rate)
            self.buckets[uuid] = bucket
        await bucket.consume(nbytes)

    # ── وضعیت ──
    def online_uuids(self) -> set[str]:
        now = time.time()
        return {u for u, ts in self.connections.items() if now - ts < 90}

    def status(self) -> dict:
        now = time.time()
        cpu = 0.0
        mem = 0.0
        try:
            cpu = round(os.getloadavg()[0] / max(1, os.cpu_count() or 1) * 100, 1)
        except Exception:
            pass
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as fh:
                info = {}
                for line in fh:
                    key, _, rest = line.partition(":")
                    info[key.strip()] = rest.strip().split()[0]
            total = int(info.get("MemTotal", "0"))
            available = int(info.get("MemAvailable", "0"))
            if total:
                mem = round((total - available) * 100 / total, 1)
        except Exception:
            pass
        online = self.online_uuids()
        total_usage = sum(self.usage.values())
        return {
            "version": settings.APP_VERSION,
            "node": settings.NODE_NAME,
            "flag": settings.NODE_FLAG,
            "uptime_seconds": int(now - self.started_at),
            "cpu": cpu,
            "mem": mem,
            "clients": len(self.users),
            "connections": int(self.active_conns),
            "users_online": len(online),
            "total_bytes": total_usage,
            "requests": self.total_requests,
            "errors": self.errors,
            "bundle_age": int(now - self.bundle_at) if self.bundle_at else -1,
            "ws_path": settings.WS_PATH,
            "xhttp_path": settings.XHTTP_PATH,
            "engine": settings.ENGINE,
            "egress_mode": _egress_summary(),
        }

    def usage_snapshot(self) -> list[dict]:
        return [{"uuid": uuid, "total": total} for uuid, total in self.usage.items()]

    def push_event(self, message: str, level: str = "info") -> None:
        self.events.append({"message": str(message)[:300], "level": level, "time": int(time.time())})
        if len(self.events) > 50:
            self.events = self.events[-50:]

    def drain_events(self) -> list[dict]:
        out, self.events = self.events, []
        return out


policy = Policy()
