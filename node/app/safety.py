"""محافظت از سرویس: کاری کنیم پنل «بن» نشود و سرویس اذیت نشود.

* بلاک پورت‌های سوءاستفاده (SMTP، SMB، IRC، ...) — جلوی شکایت‌های abuse را می‌گیرد
* محدودسازی نرخ اتصال هر IP و هر کاربر (ضد حمله/اسکن)
* ضدِ Probe: مسیرهای ناشناس زیاد = رفتار اسکنر → بلاک موقت
* محافظت از پهنای‌باند: سقف اتصال هم‌زمان کل نود
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from . import settings


class Safety:
    def __init__(self) -> None:
        self.blocked_ports = set(settings.BLOCK_PORTS)
        self.ip_hits: dict[str, deque] = defaultdict(deque)     # اتصال‌های هر IP
        self.banned: dict[str, float] = {}                      # ip → پایان بلاک
        self.probes: dict[str, deque] = defaultdict(deque)      # درخواست‌های ناشناس هر IP
        self.blocked_connects = 0
        self.blocked_ports_hits = 0
        self.probe_bans = 0

    # ── پورت‌ها ──
    def port_allowed(self, port: int) -> bool:
        if int(port) in self.blocked_ports:
            self.blocked_ports_hits += 1
            return False
        return True

    # ── نرخ اتصال ──
    def note_connect(self, ip: str) -> tuple[bool, str]:
        if self.is_banned(ip):
            self.blocked_connects += 1
            return False, "این IP موقتاً بلاک شده است"
        limit = settings.MAX_CONN_PER_IP_MIN
        if limit <= 0:
            return True, ""
        now = time.time()
        window = self.ip_hits[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            self.ban(ip, settings.BAN_SECONDS, "اتصال بیش از حد در یک دقیقه")
            self.blocked_connects += 1
            return False, "نرخ اتصال بیش از حد"
        window.append(now)
        if len(self.ip_hits) > 20000:  # جلوگیری از رشد حافظه
            for key in list(self.ip_hits)[:5000]:
                if not self.ip_hits[key]:
                    self.ip_hits.pop(key, None)
        return True, ""

    def note_probe(self, ip: str, path: str = "") -> None:
        """درخواست ناشناس/اسکنرمانند روی مسیرهای غیرپروکسی."""
        if settings.PROBE_BAN_AFTER <= 0:
            return
        now = time.time()
        window = self.probes[ip]
        while window and now - window[0] > 120:
            window.popleft()
        window.append(now)
        if len(window) >= settings.PROBE_BAN_AFTER:
            self.ban(ip, settings.BAN_SECONDS, f"اسکن مسیرها ({path[:40]})")
            self.probe_bans += 1

    def ban(self, ip: str, seconds: int, reason: str = "") -> None:
        self.banned[ip] = max(self.banned.get(ip, 0), time.time() + max(30, seconds))
        self.last_reason = reason

    def unban(self, ip: str) -> None:
        self.banned.pop(ip, None)

    def is_banned(self, ip: str) -> bool:
        until = self.banned.get(ip)
        if not until:
            return False
        if until < time.time():
            self.banned.pop(ip, None)
            return False
        return True

    def status(self) -> dict:
        now = time.time()
        return {
            "blocked_ports": sorted(self.blocked_ports),
            "blocked_port_hits": self.blocked_ports_hits,
            "banned_ips": len([ip for ip, until in self.banned.items() if until > now]),
            "blocked_connects": self.blocked_connects,
            "probe_bans": self.probe_bans,
            "max_conn_per_ip_min": settings.MAX_CONN_PER_IP_MIN,
            "max_conn_total": settings.MAX_CONN,
        }


safety = Safety()
