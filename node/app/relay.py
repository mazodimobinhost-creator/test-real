"""موتور رله: ترافیک کلاینت را از هر ترابردی به مقصد واقعی می‌رساند."""

from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import Awaitable, Callable

from . import settings
from .egress import egress
from .policy import policy
from .vless import CMD_TCP, CMD_UDP, RESPONSE_HEADER, NeedMoreData, VlessError, VlessRequest, parse_request

BUFFER = settings.READ_BUFFER

# نرخ‌های تطبیقی برای درین (شبیه AIMD در TCP)
FLOW_MIN_HW = 256 * 1024
FLOW_MAX_HW = 8 * 1024 * 1024
FLOW_START_HW = settings.DRAIN_HIGH_WATER


class AdaptiveFlow:
    """آستانه‌ی درین را با سرعت واقعی مسیر تنظیم می‌کند: سریع‌تر → بافر بزرگ‌تر."""

    __slots__ = ("high_water", "last_drain_ms")

    def __init__(self) -> None:
        self.high_water = FLOW_START_HW
        self.last_drain_ms = 0.0

    def should_drain(self, pending: int) -> bool:
        return pending > self.high_water

    async def drain(self, writer: asyncio.StreamWriter) -> None:
        t0 = asyncio.get_event_loop().time()
        await writer.drain()
        elapsed_ms = (asyncio.get_event_loop().time() - t0) * 1000
        self.last_drain_ms = elapsed_ms
        if elapsed_ms < 2.0:
            self.high_water = min(FLOW_MAX_HW, int(self.high_water * 1.5) + 65536)
        elif elapsed_ms > 25.0:
            self.high_water = max(FLOW_MIN_HW, self.high_water // 2)

SendFn = Callable[[bytes], Awaitable[None]]


def client_ip_from_headers(headers: dict, fallback: str = "?") -> str:
    fwd = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For")
    if fwd:
        return str(fwd).split(",")[0].strip()
    real = headers.get("x-real-ip") or headers.get("X-Real-IP")
    if real:
        return str(real).strip()
    return fallback or "?"


def tune_socket(writer: asyncio.StreamWriter) -> None:
    sock = writer.transport.get_extra_info("socket")
    if not sock:
        return
    with contextlib.suppress(OSError):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    for opt in (socket.SO_SNDBUF, socket.SO_RCVBUF):
        with contextlib.suppress(OSError):
            sock.setsockopt(socket.SOL_SOCKET, opt, 2 * 1024 * 1024)


async def open_tcp(address: str, port: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """اتصال به مقصد از مسیر خروج این لوکیشن (مستقیم / پروکسی IP / تانل)."""
    return await egress.connect(address, port, timeout=settings.CONNECT_TIMEOUT)


class UdpTunnel:
    """تونل UDP با فریم‌بندی ۲ بایتی طول (استاندارد VLESS)."""

    def __init__(self, send_to_client: SendFn) -> None:
        self.send_to_client = send_to_client
        self.transport: asyncio.DatagramTransport | None = None
        self.closed = asyncio.Event()

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        tunnel = self

        class Protocol(asyncio.DatagramProtocol):
            def datagram_received(self, data: bytes, addr) -> None:
                frame = len(data).to_bytes(2, "big") + data
                asyncio.create_task(tunnel.send_to_client(frame))

            def error_received(self, exc) -> None:  # noqa: D102
                policy.errors += 1

            def connection_lost(self, exc) -> None:  # noqa: D102
                tunnel.closed.set()

        _, self.transport = await loop.create_datagram_endpoint(Protocol, local_addr=("0.0.0.0", 0))

    async def feed(self, payload: bytes) -> None:
        """payload شامل چند بسته‌ی length-prefixed است."""
        pos = 0
        while pos + 2 <= len(payload):
            length = int.from_bytes(payload[pos : pos + 2], "big")
            pos += 2
            if length == 0:
                break
            chunk = payload[pos : pos + length]
            pos += length
            if self.transport and chunk:
                with contextlib.suppress(Exception):
                    self.transport.sendto(chunk, self._target)

    def set_target(self, address: str, port: int) -> None:
        self._target = (address, port)

    def close(self) -> None:
        if self.transport:
            with contextlib.suppress(Exception):
                self.transport.close()


class ClientChannel:
    """کانال کلاینت: هر ترابردی (WS یا XHTTP) این را پیاده می‌کند."""

    async def recv(self) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    async def send(self, data: bytes) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def close(self, reason: str = "") -> None:  # pragma: no cover - interface
        return None


class WsChannel(ClientChannel):
    def __init__(self, ws) -> None:
        self.ws = ws
        self.header_sent = False

    async def recv(self) -> bytes:
        msg = await self.ws.receive()
        if msg["type"] == "websocket.disconnect":
            return b""
        data = msg.get("bytes")
        if data is None:
            text = msg.get("text")
            data = text.encode() if text else b""
        return data or b""

    async def send(self, data: bytes) -> None:
        if not data:
            return
        if not self.header_sent:
            data = RESPONSE_HEADER + data
            self.header_sent = True
        await self.ws.send_bytes(data)

    async def close(self, reason: str = "") -> None:
        with contextlib.suppress(Exception):
            await self.ws.close(code=1000)


async def read_vless_request(channel: ClientChannel, max_wait: float = 30.0) -> VlessRequest:
    """اولین داده‌ی کلاینت را می‌خواند تا هدر VLESS کامل شود."""
    buf = b""
    deadline = asyncio.get_event_loop().time() + max_wait
    while True:
        if asyncio.get_event_loop().time() > deadline:
            raise VlessError("timeout waiting for vless header")
        chunk = await channel.recv()
        if not chunk:
            raise VlessError("connection closed before header")
        buf += chunk
        try:
            return parse_request(buf)
        except NeedMoreData:
            if len(buf) > 4096:
                raise VlessError("header too large")


async def run_tunnel(channel: ClientChannel, request: VlessRequest, ip: str = "?") -> None:
    """تونل کامل: احراز، محدودیت‌ها، پمپ دوطرفه."""
    uuid = request.uuid
    allowed, reason = policy.allow(uuid)
    if not allowed:
        policy.push_event(f"رد شد uuid={uuid[:8]} دلیل={reason}", "warn")
        await channel.close(reason)
        return
    if not policy.check_ip(uuid, ip):
        policy.push_event(f"محدودیت IP uuid={uuid[:8]} ip={ip}", "warn")
        await channel.close("ip limit")
        return

    user = policy.users.get(uuid) or {}
    name = user.get("name") or uuid[:8]
    policy.active_conns += 1

    try:
        if request.command == CMD_TCP:
            reader, writer = await open_tcp(request.address, request.port)
        else:
            writer = None
            reader = None
    except Exception as exc:
        policy.errors += 1
        policy.push_event(
            f"اتصال به {request.address}:{request.port} ناموفق از مسیر «{egress.active or egress.mode}»: {type(exc).__name__}",
            "error",
        )
        await channel.close("connect failed")
        return

    if request.command == CMD_UDP:
        tunnel = UdpTunnel(channel.send)
        await tunnel.start()
        tunnel.set_target(request.address, request.port)
        if request.payload:
            await tunnel.feed(request.payload)
        try:
            while True:
                chunk = await channel.recv()
                if not chunk:
                    break
                if not policy.allow(uuid)[0]:
                    break
                policy.note(uuid, len(chunk))
                policy.total_requests += 1
                await policy.throttle(uuid, len(chunk))
                await tunnel.feed(chunk)
        except Exception:
            pass
        finally:
            tunnel.close()
            await channel.close()
            policy.connections.pop(uuid, None)
            policy.active_conns = max(0, policy.active_conns - 1)
        return

    tune_socket(writer)
    if request.payload:
        writer.write(request.payload)
        policy.note(uuid, len(request.payload))
        with contextlib.suppress(Exception):
            await writer.drain()

    downlink_first = True
    flow = AdaptiveFlow()

    async def pump_up() -> None:
        try:
            while True:
                chunk = await channel.recv()
                if not chunk:
                    break
                allowed_now, _ = policy.allow(uuid)
                if not allowed_now:
                    policy.push_event(f"قطع {name}: حجم/زمان تمام شد", "warn")
                    break
                policy.note(uuid, len(chunk))
                policy.total_requests += 1
                await policy.throttle(uuid, len(chunk))
                writer.write(chunk)
                if flow.should_drain(writer.transport.get_write_buffer_size()):
                    await flow.drain(writer)
        except Exception as exc:
            policy.errors += 1
            policy.push_event(f"خطای آپلینک {name}: {type(exc).__name__}", "error")
        finally:
            with contextlib.suppress(Exception):
                writer.write_eof()

    async def pump_down() -> None:
        nonlocal downlink_first
        try:
            while True:
                data = await reader.read(BUFFER)
                if not data:
                    break
                if not policy.allow(uuid)[0]:
                    break
                policy.note(uuid, len(data))
                await policy.throttle(uuid, len(data))
                if downlink_first:
                    data = RESPONSE_HEADER + data
                    downlink_first = False
                await channel.send(data)
        except Exception as exc:
            policy.errors += 1
            policy.push_event(f"خطای دانلینک {name}: {type(exc).__name__}", "error")

    try:
        await asyncio.gather(pump_up(), pump_down(), return_exceptions=True)
    finally:
        with contextlib.suppress(Exception):
            writer.close()
        await channel.close()
        policy.connections.pop(uuid, None)
        policy.active_conns = max(0, policy.active_conns - 1)
        policy.push_event(f"قطع {name} ({ip})", "info")
