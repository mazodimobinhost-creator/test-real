"""ورودی VLESS روی TCP خام (بدون WS/XHTTP).

کاربردها:
* ترابرد TCP برای کلاینت‌هایی که WS را دوست ندارند
* نقش «پروکسی IP» برای ورکر Cloudflare (ورکر با `PROXYIP` به این پورت وصل می‌شود)
* تانل ساده بین دو سرور در شبکه‌ی داخلی Railway

با `MLP_TCP_PORT` فعال می‌شود (روی Railway: یک TCP Proxy یا پورت عمومی دوم).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from .policy import policy
from .relay import ClientChannel, client_ip_from_headers, read_vless_request, run_tunnel
from .vless import RESPONSE_HEADER

logger = logging.getLogger("mlp.node")


class TcpChannel(ClientChannel):
    """کانال کلاینت روی سوکت TCP خام."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, ip: str = "?") -> None:
        self.reader = reader
        self.writer = writer
        self.ip = ip
        self.header_sent = False

    async def recv(self) -> bytes:
        try:
            return await self.reader.read(65536)
        except Exception:
            return b""

    async def send(self, data: bytes) -> None:
        if not data:
            return
        if not self.header_sent:
            data = RESPONSE_HEADER + data
            self.header_sent = True
        with contextlib.suppress(Exception):
            self.writer.write(data)
            await self.writer.drain()

    async def close(self, reason: str = "") -> None:
        with contextlib.suppress(Exception):
            self.writer.write_eof()
        with contextlib.suppress(Exception):
            self.writer.close()


async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    ip = "?"
    with contextlib.suppress(Exception):
        peer = writer.get_extra_info("peername")
        if peer:
            ip = str(peer[0])
    channel = TcpChannel(reader, writer, ip)
    try:
        request = await read_vless_request(channel, max_wait=20.0)
    except Exception as exc:
        policy.push_event(f"هدر TCP نامعتبر از {ip}: {type(exc).__name__}", "warn")
        await channel.close()
        return
    await run_tunnel(channel, request, ip)


async def serve(port: int, host: str = "0.0.0.0") -> asyncio.AbstractServer:
    server = await asyncio.start_server(_handle, host, port)
    policy.push_event(f"ورودی TCP روی پورت {port} فعال شد", "info")
    return server


# برای سازگاری با امضای قبلی (اگر جایی استفاده شده باشد)
client_ip = client_ip_from_headers
