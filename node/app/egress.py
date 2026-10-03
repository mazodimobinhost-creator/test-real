"""مسیر خروج نود (Egress): از کجا به اینترنت وصل شود.

هر لوکیشن می‌تواند یکی از این حالت‌ها را داشته باشد:

* `direct` — خودِ نود خروجی است (پیش‌فرض)
* `proxy`  — از طریق **پروکسی IP** (SOCKS5 / SOCKS5h / HTTP CONNECT)، حتی چند پروکسی
* `chain`  — **تانل** از طریق یک سرور VLESS بالادستی (نود دیگر، ورکر یا هر سرور VLESS)
* `auto`   — اگر خروجی تنظیم شده باشد اول آن، و در صورت خرابی، مسیر سالم بعدی

پیکربندی از پنل می‌آید (باندل sync) و روی env هم قابل تنظیم است.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import ipaddress
import logging
import socket
import time

from . import settings, vless_client

logger = logging.getLogger("mlp.node")

DIRECT = "direct"
PROXY = "proxy"
CHAIN = "chain"
AUTO = "auto"
MODES = (DIRECT, PROXY, CHAIN, AUTO)

COOLDOWN_SECONDS = 60.0


def _split_hostport(raw: str, default_port: int = 1080) -> tuple[str, int]:
    raw = raw.strip()
    if not raw:
        return "", 0
    if raw.startswith("["):  # IPv6
        host, _, rest = raw[1:].partition("]")
        port = int(rest.lstrip(":") or default_port)
        return host, port
    if raw.count(":") == 1:
        host, _, port = raw.partition(":")
        return host, int(port or default_port)
    return raw, default_port


def parse_proxy_entry(entry: str, default_type: str = "socks5h", default_port: int = 1080) -> dict:
    """نمونه‌ها: `1.2.3.4:1080` · `user:pass@1.2.3.4:1080` · `http://1.2.3.4:8080`"""
    entry = entry.strip()
    if not entry:
        return {}
    ptype = default_type
    if "://" in entry:
        ptype, _, entry = entry.partition("://")
        ptype = ptype.strip().lower()
    user = password = ""
    if "@" in entry:
        creds, _, entry = entry.rpartition("@")
        user, _, password = creds.partition(":")
    host, port = _split_hostport(entry, default_port)
    if not host:
        return {}
    return {"type": ptype, "host": host, "port": port, "user": user, "password": password}


class Path:
    """یک مسیر خروج (کاندید) با آمار سلامت."""

    def __init__(self, kind: str, conf: dict) -> None:
        self.kind = kind
        self.conf = conf
        self.successes = 0
        self.failures = 0
        self.latency_ms = 0.0
        self.last_error = ""
        self.cooldown_until = 0.0
        self.bytes = 0

    @property
    def label(self) -> str:
        if self.kind == DIRECT:
            return "مستقیم"
        if self.kind == PROXY:
            auth = "🔑" if self.conf.get("user") else ""
            return f"{self.conf.get('type', 'socks5h')}://{self.conf.get('host')}:{self.conf.get('port')}{auth}"
        return f"چین VLESS → {self.conf.get('host')}:{self.conf.get('port')}{self.conf.get('path', '/ws')}"

    def in_cooldown(self) -> bool:
        return time.time() < self.cooldown_until

    def ok(self, latency_ms: float) -> None:
        self.successes += 1
        self.cooldown_until = 0.0
        self.last_error = ""
        # میانگین متحرک وزن‌دار (EWMA)
        self.latency_ms = latency_ms if not self.latency_ms else self.latency_ms * 0.7 + latency_ms * 0.3

    def fail(self, error: str) -> None:
        self.failures += 1
        self.last_error = error[:200]
        if self.failures >= 2:
            self.cooldown_until = time.time() + COOLDOWN_SECONDS

    def status(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "latency_ms": round(self.latency_ms, 1),
            "successes": self.successes,
            "failures": self.failures,
            "cooldown": max(0, round(self.cooldown_until - time.time())),
            "last_error": self.last_error,
            "bytes": self.bytes,
        }


class _PrefixedReader:
    """reader با بایت‌های باقی‌مانده از دست‌دادن پروکسی."""

    def __init__(self, reader: asyncio.StreamReader, leftover: bytes) -> None:
        self.reader = reader
        self.leftover = leftover

    async def read(self, n: int = 65536) -> bytes:
        if self.leftover:
            data, self.leftover = self.leftover, b""
            return data
        return await self.reader.read(n)


async def _socks5_connect(conf: dict, host: str, port: int, timeout: float) -> tuple:
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(conf["host"], int(conf["port"])), timeout=timeout
    )
    try:
        user, password = conf.get("user") or "", conf.get("password") or ""
        writer.write(b"\x05\x02\x00\x02" if user else b"\x05\x01\x00")
        await writer.drain()
        greeting = await asyncio.wait_for(reader.readexactly(2), timeout)
        if greeting[0] != 5:
            raise ConnectionError("پاسخ نامعتبر از پروکسی SOCKS5")
        method = greeting[1]
        if method == 2:
            u = user.encode()[:255]
            p = password.encode()[:255]
            writer.write(bytes([1, len(u)]) + u + bytes([len(p)]) + p)
            await writer.drain()
            auth = await asyncio.wait_for(reader.readexactly(2), timeout)
            if auth[1] != 0:
                raise PermissionError("نام کاربری/رمز پروکسی رد شد")
        elif method == 0xFF:
            raise PermissionError("پروکسی روش احراز را قبول نکرد")

        # نوع پروکسی: socks5 = DNS محلی، socks5h = DNS روی پروکسی
        address = host
        use_domain = conf.get("type", "socks5h").lower() != "socks5"
        if not use_domain:
            with contextlib.suppress(Exception):
                address = socket.gethostbyname(host)
        try:
            ip = ipaddress.ip_address(address)
            atyp = 1 if ip.version == 4 else 4
            encoded = ip.packed
        except ValueError:
            raw = address.encode("idna") if address.isascii() else address.encode()
            atyp, encoded = 3, bytes([len(raw)]) + raw
        writer.write(b"\x05\x01\x00" + bytes([atyp]) + encoded + int(port).to_bytes(2, "big"))
        await writer.drain()
        reply = await asyncio.wait_for(reader.readexactly(4), timeout)
        if reply[1] != 0:
            raise ConnectionError(f"پروکسی مقصد را رد کرد (کد {reply[1]})")
        atyp_reply = reply[3]
        skip = 4 if atyp_reply == 1 else (16 if atyp_reply == 4 else (await asyncio.wait_for(reader.readexactly(1), timeout))[0])
        await asyncio.wait_for(reader.readexactly(skip + 2), timeout)
        return reader, writer, b""
    except Exception:
        with contextlib.suppress(Exception):
            writer.close()
        raise


async def _http_connect(conf: dict, host: str, port: int, timeout: float) -> tuple:
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(conf["host"], int(conf["port"])), timeout=timeout
    )
    try:
        lines = [f"CONNECT {host}:{port} HTTP/1.1", f"Host: {host}:{port}", "Proxy-Connection: keep-alive"]
        if conf.get("user"):
            token = base64.b64encode(f"{conf['user']}:{conf.get('password') or ''}".encode()).decode()
            lines.append(f"Proxy-Authorization: Basic {token}")
        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode())
        await writer.drain()
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = await asyncio.wait_for(reader.read(1024), timeout)
            if not chunk:
                raise ConnectionError("پروکسی HTTP اتصال را بست")
            head += chunk
            if len(head) > 8192:
                raise ConnectionError("پاسخ پروکسی HTTP طولانی بود")
        status_line = head.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        if " 200" not in status_line:
            raise ConnectionError(f"پروکسی HTTP: {status_line[:80]}")
        leftover = head.split(b"\r\n\r\n", 1)[1]
        return reader, writer, leftover
    except Exception:
        with contextlib.suppress(Exception):
            writer.close()
        raise


class Egress:
    """مدیر مسیر خروج: انتخاب، اتصال، آمار و تست."""

    def __init__(self) -> None:
        self.mode = DIRECT
        self.fallback = True
        self.test_target = settings.EGRESS_TEST_TARGET
        self.probe_seconds = settings.EGRESS_PROBE
        self.paths: list[Path] = []
        self.active: str = ""
        self.total_conns = 0
        self.total_failovers = 0
        self.apply_config(self.from_env())

    # ───────────── پیکربندی ─────────────
    def from_env(self) -> dict:
        return {
            "mode": settings.EGRESS,
            "fallback": settings.EGRESS_FALLBACK,
            "test_target": settings.EGRESS_TEST_TARGET,
            "proxy": {
                "type": settings.PROXY_TYPE,
                "list": settings.PROXY_LIST,
                "rotate": settings.PROXY_ROTATE,
            },
            "chain": settings.chain_config(),
        }

    def apply_config(self, conf: dict | None) -> None:
        """پیکربندی را (از env یا از باندل پنل) اعمال می‌کند."""
        conf = conf or {}
        mode = str(conf.get("mode") or DIRECT).strip().lower()
        self.mode = mode if mode in MODES else DIRECT
        self.fallback = bool(conf.get("fallback", True))
        self.test_target = str(conf.get("test_target") or settings.EGRESS_TEST_TARGET)

        proxy = conf.get("proxy") or {}
        chain = conf.get("chain") or {}
        ptype = str(proxy.get("type") or settings.PROXY_TYPE).strip().lower()
        entries = proxy.get("list")
        if isinstance(entries, str):
            entries = [x for x in entries.replace(",", "\n").splitlines() if x.strip()]
        entries = [str(x) for x in (entries or []) if str(x).strip()]
        if not entries and settings.PROXY_LIST:
            entries = list(settings.PROXY_LIST)

        paths: list[Path] = []
        for raw in entries:
            parsed = parse_proxy_entry(raw, ptype, settings.PROXY_PORT)
            if not parsed:
                continue
            if not parsed.get("user") and settings.PROXY_USER and len(entries) == 1:
                parsed.update({"user": settings.PROXY_USER, "password": settings.PROXY_PASS})
            paths.append(Path(PROXY, parsed))
        if not paths and settings.PROXY_HOST:
            paths.append(Path(PROXY, {
                "type": ptype, "host": settings.PROXY_HOST, "port": settings.PROXY_PORT,
                "user": settings.PROXY_USER, "password": settings.PROXY_PASS,
            }))

        chain_host = str(chain.get("host") or "").strip()
        if chain_host:
            paths.append(Path(CHAIN, {
                "host": chain_host,
                "port": int(chain.get("port") or 443),
                "path": str(chain.get("path") or "/ws"),
                "uuid": str(chain.get("uuid") or "").strip(),
                "tls": bool(chain.get("tls", True)),
                "sni": str(chain.get("sni") or "").strip(),
                "insecure": bool(chain.get("insecure", False)),
            }))

        self.paths = paths
        self.rotate = str(proxy.get("rotate") or settings.PROXY_ROTATE).strip().lower()
        self._order_cache = ""

    def configured(self) -> bool:
        return bool(self.paths)

    def _candidates(self) -> list[Path]:
        if not self.paths:
            return [Path(DIRECT, {})]
        ordered = list(self.paths)
        if self.rotate == "fastest":
            ordered.sort(key=lambda p: (p.latency_ms or 9999, p.failures))
        elif self.rotate == "roundrobin" and ordered:
            self._rr = getattr(self, "_rr", 0) + 1
            ordered = ordered[self._rr % len(ordered):] + ordered[: self._rr % len(ordered)]
        live = [p for p in ordered if not p.in_cooldown()]
        out = live or ordered
        if self.mode == AUTO and self.fallback:
            out = out + [Path(DIRECT, {})]
        return out

    # ───────────── اتصال ─────────────
    async def connect(self, host: str, port: int, timeout: float | None = None):
        """اتصال به مقصد از مسیر خروج انتخاب‌شده (با failover در حالت auto)."""
        timeout = timeout or settings.CONNECT_TIMEOUT
        candidates = self._candidates() if self.mode != DIRECT else [Path(DIRECT, {})]
        last_error = ""
        for index, path in enumerate(candidates):
            started = time.time()
            try:
                reader, writer = await self._open(path, host, port, timeout)
                path.ok((time.time() - started) * 1000)
                self.active = path.label
                self.total_conns += 1
                if index:
                    self.total_failovers += 1
                return reader, writer
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                path.fail(last_error)
                logger.warning("egress %s failed for %s:%s → %s", path.label, host, port, last_error)
                if index + 1 < len(candidates):
                    continue
                raise
        raise ConnectionError(last_error or "no egress path available")

    async def _open(self, path: Path, host: str, port: int, timeout: float):
        if path.kind == DIRECT:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host=host, port=port), timeout=timeout)
            return reader, writer
        if path.kind == PROXY:
            kind = (path.conf.get("type") or "socks5h").lower()
            if kind in ("http", "https", "http-connect", "connect"):
                reader, writer, leftover = await _http_connect(path.conf, host, port, timeout)
                return (_PrefixedReader(reader, leftover) if leftover else reader), writer
            return (await _socks5_connect(path.conf, host, port, timeout))[:2]
        # chain (تانل VLESS)
        conf = path.conf
        if not conf.get("uuid"):
            raise vless_client.ChainError("UUID سرور بالادستی تنظیم نشده است")
        reader, writer = await vless_client.open_stream(
            conf["host"], int(conf["port"]), conf.get("path") or "/ws", conf["uuid"],
            tls=bool(conf.get("tls", True)), sni=conf.get("sni") or "",
            target_host=host, target_port=port, timeout=timeout,
            insecure=bool(conf.get("insecure")),
        )
        return reader, writer

    # ───────────── تست و آمار ─────────────
    async def test_path(self, path: Path, target: tuple[str, int] | None = None, timeout: float = 8.0) -> dict:
        host, port = target or self._target()
        started = time.time()
        try:
            reader, writer = await self._open(path, host, port, timeout)
            latency = (time.time() - started) * 1000
            path.ok(latency)
            with contextlib.suppress(Exception):
                writer.close()
            return {"label": path.label, "kind": path.kind, "ok": True, "latency_ms": round(latency, 1),
                    "target": f"{host}:{port}"}
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            path.fail(error)
            return {"label": path.label, "kind": path.kind, "ok": False, "error": error[:200],
                    "target": f"{host}:{port}"}

    def _target(self) -> tuple[str, int]:
        host, _, port = (self.test_target or "1.1.1.1:443").partition(":")
        return host or "1.1.1.1", int(port or 443)

    async def test_all(self, target: tuple[str, int] | None = None) -> dict:
        paths = self.paths or [Path(DIRECT, {})]
        results = []
        for path in paths:
            results.append(await self.test_path(path, target))
        if self.mode == AUTO and (not results or not any(r["ok"] for r in results)) and self.paths:
            results.append(await self.test_path(Path(DIRECT, {}), target))
        return {
            "mode": self.mode,
            "target": "{}:{}".format(*self._target()),
            "results": results,
            "any_ok": any(r["ok"] for r in results),
        }

    def status(self) -> dict:
        return {
            "mode": self.mode,
            "configured": self.configured(),
            "fallback": self.fallback,
            "active": self.active,
            "connections": self.total_conns,
            "failovers": self.total_failovers,
            "test_target": self.test_target,
            "paths": [p.status() for p in (self.paths or [Path(DIRECT, {})])],
        }

    async def probe_loop(self) -> None:
        if not self.probe_seconds:
            return
        await asyncio.sleep(20)
        while True:
            try:
                await self.test_all()
            except Exception as exc:  # pragma: no cover
                logger.warning("egress probe error: %s", exc)
            await asyncio.sleep(self.probe_seconds)


egress = Egress()
