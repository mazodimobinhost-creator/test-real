"""محافظت از خودِ پنل: ضدِ اسکن/حمله/بن‌شدن.

* محدودسازی نرخ درخواست هر IP روی پنل
* شناسایی رفتار اسکنر (مسیرهای ناموجود پشت‌سرهم) و بلاک موقت
* مسیرهای API/پنل از نظر کرالر پنهان می‌مانند و مسیر مخفی پنل اصلاً به بیرون لو نمی‌رود
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import PlainTextResponse

RATE_WINDOW = 60.0
RATE_LIMIT = 240          # درخواست در دقیقه برای هر IP
PROBE_LIMIT = 60          # مسیر ناموجود در ۲ دقیقه → بلاک
BAN_SECONDS = 900

_hits: dict[str, deque] = defaultdict(deque)
_probes: dict[str, deque] = defaultdict(deque)
_banned: dict[str, float] = {}
_blocked_requests = 0
_probe_bans = 0

# مسیرهایی که هرگز نباید در لاگ/پاسخ لو بروند
HIDDEN_PREFIXES = ("/api/", "/sub/")


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip") or ""
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _prune(window: deque, now: float, window_seconds: float) -> None:
    while window and now - window[0] > window_seconds:
        window.popleft()


def is_banned(ip: str) -> bool:
    until = _banned.get(ip)
    if not until:
        return False
    if until < time.time():
        _banned.pop(ip, None)
        return False
    return True


def ban(ip: str, seconds: int = BAN_SECONDS) -> None:
    _banned[ip] = time.time() + max(60, seconds)


def unban(ip: str) -> None:
    _banned.pop(ip, None)


def status() -> dict:
    now = time.time()
    return {
        "active_bans": len([ip for ip, until in _banned.items() if until > now]),
        "blocked_requests": _blocked_requests,
        "probe_bans": _probe_bans,
        "rate_limit_per_min": RATE_LIMIT,
        "probe_limit": PROBE_LIMIT,
    }


async def middleware(request: Request, call_next):
    global _blocked_requests, _probe_bans
    ip = client_ip(request)
    now = time.time()

    if is_banned(ip):
        _blocked_requests += 1
        return PlainTextResponse("Too Many Requests", status_code=429)

    window = _hits[ip]
    _prune(window, now, RATE_WINDOW)
    window.append(now)
    if len(window) > RATE_LIMIT:
        if len(window) > RATE_LIMIT * 3:   # فقط رفتار خیلی پرتکرار بلاک می‌شود
            ban(ip)
        _blocked_requests += 1
        return PlainTextResponse("Too Many Requests", status_code=429)

    response = await call_next(request)

    # رفتار اسکنری: مسیرهای ناموجود پشت‌سرهم (پنل مسیر مخفی دارد، پس این‌ها مشکوک‌اند)
    path = request.url.path
    if response.status_code == 404 and not path.startswith(HIDDEN_PREFIXES):
        probes = _probes[ip]
        _prune(probes, now, 120.0)
        probes.append(now)
        if len(probes) >= PROBE_LIMIT:
            ban(ip)
            _probe_bans += 1

    if len(_hits) > 50000:                 # جلوگیری از رشد حافظه
        for key in list(_hits)[:10000]:
            if not _hits[key]:
                _hits.pop(key, None)
    if len(_probes) > 50000:
        for key in list(_probes)[:10000]:
            if not _probes[key]:
                _probes.pop(key, None)
    return response
