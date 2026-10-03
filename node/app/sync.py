"""ارتباط نود با پنل: گرفتن باندل کاربران و فرستادن گزارش مصرف."""

from __future__ import annotations

import asyncio
import logging

import httpx

from . import settings
from .policy import policy

logger = logging.getLogger("mlp.node")
_client: httpx.AsyncClient | None = None
_panel_ok = False
_last_error = ""


def http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {settings.NODE_TOKEN}",
                "User-Agent": f"MLP-Node/{settings.APP_VERSION}",
                "Accept": "application/json",
            },
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def panel_ok() -> bool:
    return _panel_ok


def last_error() -> str:
    return _last_error


async def sync_once() -> bool:
    """باندل تازه را می‌گیرد (و وضعیت خودش را هم می‌فرستد)."""
    global _panel_ok, _last_error
    if not settings.PANEL_URL or not settings.NODE_TOKEN:
        _last_error = "MLP_PANEL_URL یا MLP_NODE_TOKEN تنظیم نشده است"
        _panel_ok = False
        return False
    url = f"{settings.PANEL_URL}/api/node/sync"
    try:
        resp = await http().post(url, json={"status": policy.status(), "version": settings.APP_VERSION})
        if resp.status_code != 200:
            _last_error = f"HTTP {resp.status_code}: {resp.text[:160]}"
            _panel_ok = False
            return False
        bundle = resp.json()
        if not bundle.get("ok"):
            _last_error = "پاسخ نامعتبر از پنل"
            _panel_ok = False
            return False
        before = len(policy.users)
        policy.apply_bundle(bundle)
        _panel_ok = True
        _last_error = ""
        if before != len(policy.users):
            policy.push_event(f"باندل به‌روزرسانی شد: {len(policy.users)} کاربر", "info")
        return True
    except Exception as exc:
        _last_error = f"{type(exc).__name__}: {exc}"[:200]
        _panel_ok = False
        return False


async def report_once() -> bool:
    """مصرف تجمعی هر کاربر + وضعیت را به پنل می‌فرستد."""
    global _panel_ok, _last_error
    if not settings.PANEL_URL or not settings.NODE_TOKEN:
        return False
    usage = policy.usage_snapshot()
    if not usage and not policy.events:
        # چیزی برای گفتن نیست، ولی heartbeat وضعیت را می‌فرستیم
        pass
    payload = {"usage": usage, "status": policy.status(), "events": policy.drain_events()}
    try:
        resp = await http().post(f"{settings.PANEL_URL}/api/node/report", json=payload)
        if resp.status_code != 200:
            _last_error = f"HTTP {resp.status_code}: {resp.text[:160]}"
            return False
        _panel_ok = True
        _last_error = ""
        return True
    except Exception as exc:
        _last_error = f"{type(exc).__name__}: {exc}"[:200]
        _panel_ok = False
        return False


async def sync_loop() -> None:
    await asyncio.sleep(1)
    while True:
        ok = await sync_once()
        if not ok:
            logger.warning("sync failed: %s", _last_error)
        await asyncio.sleep(max(5.0, settings.SYNC_INTERVAL if ok else 10.0))


async def report_loop() -> None:
    await asyncio.sleep(3)
    while True:
        try:
            await report_once()
        except Exception as exc:
            logger.warning("report failed: %s", exc)
        await asyncio.sleep(max(5.0, settings.REPORT_INTERVAL))
