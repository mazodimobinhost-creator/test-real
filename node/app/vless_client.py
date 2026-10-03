"""کلاینت VLESS برای «تانل/چین»: نود می‌تواند از طریق یک سرور دیگر به اینترنت وصل شود.

یعنی یک لوکیشن می‌تواند خروجی‌اش را از لوکیشن دیگری (یا هر سرور VLESS دیگر،
حتی ورکر Cloudflare) بگیرد؛ کاربر فقط یک نود می‌بیند ولی IP خروجی آن یکی است.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import ssl
import uuid as uuid_lib

try:  # نسخه‌های مختلف websockets امضای متفاوتی دارند
    import websockets
except Exception:  # pragma: no cover - اگر نصب نباشد، حالت چین کار نمی‌کند
    websockets = None  # type: ignore

ATYP_IPV4 = 1
ATYP_DOMAIN = 2
ATYP_IPV6 = 3


class ChainError(RuntimeError):
    """خطای برقراری تانل به سرور بالادستی."""


def build_request_header(uuid_str: str, host: str, port: int, command: int = 1) -> bytes:
    """هدر درخواست VLESS برای مقصد مشخص (همان قالب استاندارد)."""
    try:
        uid = uuid_lib.UUID(uuid_str).bytes
    except Exception as exc:
        raise ChainError(f"UUID نامعتبر برای چین: {exc}") from exc
    head = bytes([0]) + uid + bytes([0, command]) + int(port).to_bytes(2, "big")
    with contextlib.suppress(ValueError):
        ip = ipaddress.ip_address(host)
        if ip.version == 4:
            return head + bytes([ATYP_IPV4]) + ip.packed
        return head + bytes([ATYP_IPV6]) + ip.packed
    raw = host.encode("idna") if host.isascii() else host.encode("utf-8")
    return head + bytes([ATYP_DOMAIN, len(raw)]) + raw


class _FakeTransport:
    """جای transport سوکت را می‌گیرد تا کد رله بدون تغییر کار کند."""

    def __init__(self, owner: "_WsWriter") -> None:
        self.owner = owner

    def get_write_buffer_size(self) -> int:
        return len(self.owner.buf)

    def get_extra_info(self, name: str, default=None):
        return default


class _WsWriter:
    def __init__(self, ws) -> None:
        self.ws = ws
        self.buf = bytearray()
        self.transport = _FakeTransport(self)
        self._closed = False

    def write(self, data: bytes) -> None:
        if data:
            self.buf += data

    async def drain(self) -> None:
        if not self.buf:
            return
        data, self.buf = bytes(self.buf), bytearray()
        await self.ws.send(data)

    def write_eof(self) -> None:
        return None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        async def _closer() -> None:
            with contextlib.suppress(Exception):
                await self.ws.close()

        with contextlib.suppress(RuntimeError):
            asyncio.get_running_loop().create_task(_closer())

    async def wait_closed(self) -> None:
        with contextlib.suppress(Exception):
            await self.ws.wait_closed()


class _WsReader:
    """جریان بایت روی پیام‌های WebSocket (شامل حذف هدر ۲ بایتی پاسخ)."""

    def __init__(self, ws, queue: asyncio.Queue, task: asyncio.Task) -> None:
        self.ws = ws
        self.queue = queue
        self.task = task

    async def read(self, _n: int = 65536) -> bytes:
        data = await self.queue.get()
        return data

    async def aclose(self) -> None:
        self.task.cancel()
        with contextlib.suppress(Exception):
            await self.ws.close()


async def open_stream(
    host: str,
    port: int,
    path: str,
    uuid_str: str,
    *,
    tls: bool = True,
    sni: str = "",
    target_host: str,
    target_port: int,
    timeout: float = 12.0,
    insecure: bool = False,
    extra_headers: dict[str, str] | None = None,
) -> tuple[_WsReader, _WsWriter]:
    """تانل VLESS/WS به سرور بالادستی و باز کردن مقصد از آن‌جا."""
    if websockets is None:
        raise ChainError("بسته‌ی websockets نصب نیست (pip install websockets)")
    scheme = "wss" if tls else "ws"
    netloc = host if (":" not in host or host.startswith("[")) else f"[{host}]"
    if (tls and port != 443) or ((not tls) and port != 80):
        netloc = f"{netloc}:{port}"
    uri = f"{scheme}://{netloc}{path if path.startswith('/') else '/' + path}"

    ssl_ctx = None
    if tls:
        ssl_ctx = ssl.create_default_context()
        if sni:
            ssl_ctx.server_hostname = sni
        if insecure:
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

    # UA باید غیرمرورگر باشد تا نود بالادستی آن را «بازدیدکننده» نگیرد
    headers = {"User-Agent": "MLP-Node-Chain/1.1", "Host": sni or host}
    if extra_headers:
        headers.update(extra_headers)

    kwargs: dict = {"open_timeout": timeout, "close_timeout": 5, "max_size": None, "ping_interval": 20}
    if ssl_ctx is not None:
        kwargs["ssl"] = ssl_ctx
    if sni:
        kwargs["server_hostname"] = sni

    try:
        try:
            ws = await websockets.connect(uri, additional_headers=headers, **kwargs)  # type: ignore[attr-defined]
        except TypeError:  # websockets < 14
            ws = await websockets.connect(uri, extra_headers=headers, **kwargs)
    except Exception as exc:
        raise ChainError(f"اتصال به سرور بالادستی ناموفق: {type(exc).__name__}: {exc}") from exc

    # هدر درخواست VLESS + اولین بایت‌های کلاینت در همان پیام اول
    with contextlib.suppress(Exception):
        await ws.send(build_request_header(uuid_str, target_host, target_port))

    queue: asyncio.Queue = asyncio.Queue()

    async def pump() -> None:
        first = True
        try:
            async for message in ws:
                data = bytes(message) if not isinstance(message, str) else message.encode()
                if first:
                    if data[:2] == b"\x00\x00":
                        data = data[2:]
                    first = False
                    if not data:
                        continue
                await queue.put(data)
        except Exception:
            pass
        finally:
            with contextlib.suppress(Exception):
                await queue.put(b"")
                await ws.close()

    task = asyncio.create_task(pump())
    return _WsReader(ws, queue, task), _WsWriter(ws)
