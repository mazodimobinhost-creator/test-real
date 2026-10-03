"""ترابرد XHTTP (SplitHTTP) — حالت‌های stream-up و packet-up.

آپلینک: POST روی `{path}/{session}` (stream-up) یا `{path}/{session}/{seq}` (packet-up)
دانلینک: GET روی `{path}/{session}` که یک استریم پیوسته برمی‌گرداند.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import settings
from .policy import policy
from .relay import ClientChannel, client_ip_from_headers, read_vless_request, run_tunnel
from .vless import RESPONSE_HEADER

router = APIRouter()

_sessions: dict[str, "XhttpSession"] = {}
_reaper_task: asyncio.Task | None = None

RESP_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "X-Accel-Buffering": "no",
    "Content-Type": "application/octet-stream",
}


class XhttpChannel(ClientChannel):
    def __init__(self) -> None:
        self.up_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=1024)
        self.down_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=2048)
        self.closed = False

    async def feed(self, data: bytes) -> None:
        if data and not self.closed:
            await self.up_q.put(data)

    async def recv(self) -> bytes:
        item = await self.up_q.get()
        return item or b""

    async def send(self, data: bytes) -> None:
        if data:
            await self.down_q.put(data)

    async def close(self, reason: str = "") -> None:
        self.closed = True
        try:
            self.up_q.put_nowait(None)
        except Exception:
            pass
        try:
            self.down_q.put_nowait(None)
        except Exception:
            pass


class XhttpSession:
    def __init__(self, session_id: str, mode: str, ip: str) -> None:
        self.id = session_id
        self.mode = mode
        self.ip = ip
        self.channel = XhttpChannel()
        self.task: asyncio.Task | None = None
        self.created = time.time()
        self.last_seen = time.time()
        self.closed = False
        self.first_body = b""
        self.started = False
        self.seq_buf: dict[int, bytes] = {}
        self.next_seq = 0
        self.downlink_open = False

    def touch(self) -> None:
        self.last_seen = time.time()


def _get_session(session_id: str, mode: str, ip: str) -> XhttpSession:
    session = _sessions.get(session_id)
    if session is None:
        session = XhttpSession(session_id, mode, ip)
        _sessions[session_id] = session
        policy.push_event(f"سشن XHTTP[{mode}] جدید {session_id[:8]} از {ip}", "info")
    session.touch()
    return session


async def _runner(session: XhttpSession) -> None:
    """منتظر اولین داده (هدر VLESS) می‌ماند و بعد تونل را اجرا می‌کند."""
    try:
        request = await read_vless_request(session.channel, max_wait=60.0)
        session.started = True
        await run_tunnel(session.channel, request, session.ip)
    except Exception as exc:
        policy.push_event(f"خطای سشن {session.id[:8]}: {type(exc).__name__}", "error")
    finally:
        session.closed = True
        await session.channel.close()


def _ensure_runner(session: XhttpSession) -> None:
    if session.task is None:
        session.task = asyncio.create_task(_runner(session))


async def _reaper() -> None:
    while True:
        await asyncio.sleep(15)
        now = time.time()
        for sid, session in list(_sessions.items()):
            if session.closed or (now - session.last_seen > settings.SESSION_IDLE_TIMEOUT and not session.started):
                if session.task:
                    session.task.cancel()
                await session.channel.close()
                _sessions.pop(sid, None)


def start_reaper() -> None:
    global _reaper_task
    if _reaper_task is None or _reaper_task.done():
        _reaper_task = asyncio.create_task(_reaper())


@router.post("/{session_id}")
async def xhttp_upload(request: Request, session_id: str):
    """stream-up: یک POST پیوسته."""
    start_reaper()
    ip = client_ip_from_headers(dict(request.headers), request.client.host if request.client else "?")
    session = _get_session(session_id, "stream-up", ip)
    _ensure_runner(session)
    total = 0
    async for chunk in request.stream():
        if not chunk:
            continue
        total += len(chunk)
        if total > settings.MAX_BODY:
            break
        session.touch()
        await session.channel.feed(chunk)
    return JSONResponse({"ok": True, "bytes": total}, headers=RESP_HEADERS)


@router.post("/{session_id}/{seq}")
async def xhttp_upload_packet(request: Request, session_id: str, seq: int):
    """packet-up: چند POST با شماره‌ی ترتیب."""
    start_reaper()
    ip = client_ip_from_headers(dict(request.headers), request.client.host if request.client else "?")
    session = _get_session(session_id, "packet-up", ip)
    _ensure_runner(session)
    body = await request.body()
    if len(body) > settings.MAX_BODY:
        return JSONResponse({"ok": False, "error": "too large"}, status_code=413)
    session.touch()
    if seq == 0:
        await session.channel.feed(body)
    else:
        session.seq_buf[seq] = body
        while (session.next_seq or 1) in session.seq_buf:
            nxt = session.next_seq or 1
            await session.channel.feed(session.seq_buf.pop(nxt))
            session.next_seq = nxt + 1
    return JSONResponse({"ok": True, "bytes": len(body)}, headers=RESP_HEADERS)


@router.get("/{session_id}")
async def xhttp_download(request: Request, session_id: str):
    """دانلینک: استریم پیوسته از مقصد به کلاینت."""
    start_reaper()
    ip = client_ip_from_headers(dict(request.headers), request.client.host if request.client else "?")
    session = _get_session(session_id, "download", ip)
    session.downlink_open = True
    _ensure_runner(session)

    # اگر کلاینت early-data فرستاده باشد (پارامتر ed) اینجا نادیده گرفته می‌شود؛
    # داده‌ی اصلی از مسیر POST می‌آید.

    async def gen():
        first = True
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(session.channel.down_q.get(), timeout=120)
                except asyncio.TimeoutError:
                    break
                if chunk is None:
                    break
                session.touch()
                if first:
                    chunk = RESPONSE_HEADER + chunk
                    first = False
                yield chunk
        finally:
            session.downlink_open = False

    return StreamingResponse(gen(), headers=RESP_HEADERS, media_type="application/octet-stream")
