"""سرویس نود: رله‌ی VLESS روی یک پورت واحد (همان چیزی که Railway می‌دهد).

دو موتور دارد:
  * `MLP_ENGINE=python` (پیش‌فرض): رله‌ی پایتونی با اعمال کامل حجم/انقضا/سرعت/IP
  * `MLP_ENGINE=xray`: Xray-core به‌عنوان دیتاپلین (سرعت بالاتر) و این سرویس
    نقش کنترل‌پلین و «سایت پوششی» را دارد
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os

import httpx
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from . import decoy, settings, sync, xhttp
from .policy import policy
from .relay import WsChannel, client_ip_from_headers, read_vless_request, run_tunnel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("mlp.node")

USE_XRAY = settings.ENGINE == "xray"

app = FastAPI(title="Web", docs_url=None, redoc_url=None)

from .xhttp import xhttp_download, xhttp_upload, xhttp_upload_packet

if USE_XRAY:
    from .xray_engine import engine as xray_engine
else:
    xray_engine = None  # type: ignore


def xray_active() -> bool:
    """موتور Xray واقعاً در حال اجراست؟ (اگر نه، خودکار به موتور پایتون برمی‌گردیم)"""
    return bool(USE_XRAY and xray_engine is not None and xray_engine.is_running())


# ───────────────────────────── چرخه‌ی عمر ─────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "node starting · engine=%s name=%s panel=%s decoy=%s",
        settings.ENGINE,
        settings.NODE_NAME,
        settings.PANEL_URL or "(unset)",
        settings.DECOY,
    )
    asyncio.create_task(sync.sync_loop())
    asyncio.create_task(sync.report_loop())
    if USE_XRAY and xray_engine is not None:
        await asyncio.to_thread(xray_engine.start)
        asyncio.create_task(xray_engine.stats_loop())
        asyncio.create_task(_xray_watchdog())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await sync.close()
    if xray_engine is not None:
        xray_engine.stop()


async def _xray_watchdog() -> None:
    """هر بار که باندل عوض می‌شود، کاربران Xray را هم به‌روز می‌کند."""
    last_version = -1
    while True:
        try:
            if policy.bundle_version != last_version:
                last_version = policy.bundle_version
                await asyncio.to_thread(xray_engine.apply)
        except Exception as exc:
            logger.warning("xray watchdog error: %s", exc)
        await asyncio.sleep(9)


# ───────────────────────────── سلامت و اطلاعات ─────────────────────────────
def _masked_ok() -> dict:
    """پاسخ بی‌اثر: هیچ اطلاعاتی از نقش سرور لو نمی‌دهد."""
    return {"status": "ok"}


def _authorized(request: Request) -> bool:
    key = request.query_params.get("key") or request.headers.get("x-node-key") or ""
    return bool(key) and key == settings.NODE_TOKEN


@app.get("/healthz")
async def healthz(request: Request):
    """بدون کلید، فقط وضعیت عمومی؛ با `?key=<توکن نود>` جزئیات کامل."""
    if not _authorized(request):
        return JSONResponse(_masked_ok())
    status = policy.status()
    status.update(
        {
            "ok": True,
            "service": "mlp-node",
            "role": "node",
            "engine": settings.ENGINE,
            "panel_ok": sync.panel_ok(),
            "panel_error": sync.last_error(),
            "panel_url": settings.PANEL_URL,
        }
    )
    if xray_engine is not None:
        status["xray"] = xray_engine.status()
    return JSONResponse(status)


@app.get("/info")
async def info(request: Request):
    if not _authorized(request):
        return JSONResponse(_masked_ok())
    data = {
        "ok": True,
        "service": "mlp-node",
        "version": settings.APP_VERSION,
        "engine": settings.ENGINE,
        "name": settings.NODE_NAME,
        "flag": settings.NODE_FLAG,
        "ws_path": settings.WS_PATH,
        "xhttp_path": settings.XHTTP_PATH,
        "users": len(policy.users),
        "panel_ok": sync.panel_ok(),
        "decoy": settings.DECOY,
    }
    if xray_engine is not None:
        data["xray"] = xray_engine.status()
        data["selfcheck"] = xray_engine.self_check()
    return JSONResponse(data)


@app.get("/_mlp/config.js")
async def config_js():
    """فایل پیکربندی سمت کلاینت (سایت پوششی) — مسیر پروکسی را اینجا می‌گذارد."""
    return Response(
        content=f'window.__APP_CONFIG__={{version:"{settings.APP_VERSION}",api:"/api/v1"}};',
        media_type="application/javascript",
    )


# ───────────────────────────── پروکسی در موتور Xray ─────────────────────────────
if USE_XRAY:

    async def _proxy_to_xray(request: Request, target_port: int) -> Response:
        url = f"http://127.0.0.1:{target_port}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        body = await request.body()
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length", "connection", "accept-encoding")
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=None)) as client:
                resp = await client.request(request.method, url, content=body, headers=headers)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={"Content-Type": resp.headers.get("content-type", "application/octet-stream")},
            )
        except Exception:
            html, status = decoy.decoy_response(request.url.path)
            return HTMLResponse(html, status_code=status if html else 200)

    async def _xray_ws_bridge(ws: WebSocket, port: int) -> None:
        """WebSocket را به Xray داخلی پل می‌زند (پروکسی خام)."""
        await ws.accept()
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
        except Exception:
            with contextlib.suppress(Exception):
                await ws.close(code=1011)
            return

        async def ws_to_tcp() -> None:
            try:
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        break
                    data = msg.get("bytes") or (msg.get("text") or "").encode()
                    if data:
                        writer.write(bytes(data))
                        await writer.drain()
            except Exception:
                pass
            finally:
                with contextlib.suppress(Exception):
                    writer.write_eof()

        async def tcp_to_ws() -> None:
            try:
                while True:
                    data = await reader.read(128 * 1024)
                    if not data:
                        break
                    await ws.send_bytes(data)
            except Exception:
                pass
            finally:
                with contextlib.suppress(Exception):
                    await ws.close()

        await asyncio.gather(ws_to_tcp(), tcp_to_ws(), return_exceptions=True)
        with contextlib.suppress(Exception):
            writer.close()

else:

    async def _proxy_to_xray(request: Request, target_port: int) -> Response:  # pragma: no cover
        html, status = decoy.decoy_response(request.url.path)
        return HTMLResponse(html, status_code=status)

    async def _xray_ws_bridge(ws: WebSocket, port: int) -> None:  # pragma: no cover
        await ws.close(code=1011)


# ───────────────────────────── مسیرهای پروکسی ─────────────────────────────
def _is_browser(ws: WebSocket) -> bool:
    ua = (ws.headers.get("user-agent") or "").lower()
    return any(h in ua for h in ("mozilla", "chrome", "safari", "firefox", "edg", "opera"))


@app.websocket(settings.WS_PATH)
async def ws_endpoint(ws: WebSocket) -> None:
    if xray_active():
        from .xray_engine import WS_PORT

        await _xray_ws_bridge(ws, WS_PORT)
        return

    if _is_browser(ws):
        # یک بازدیدکننده‌ی کنجکاو: به‌جای خطا، سایت پوششی نشان بده
        await ws.accept()
        html, _ = decoy.decoy_response(settings.WS_PATH)
        with contextlib.suppress(Exception):
            await ws.send_text("HTTP/1.1 400 Bad Request") if False else None
            await ws.close(code=1008)
        return

    await ws.accept()
    ip = client_ip_from_headers(dict(ws.headers), ws.client.host if ws.client else "?")
    channel = WsChannel(ws)
    try:
        request = await read_vless_request(channel, max_wait=30.0)
    except Exception as exc:
        policy.push_event(f"هدر نامعتبر از {ip}: {type(exc).__name__}", "warn")
        with contextlib.suppress(Exception):
            await ws.close(code=1008)
        return
    await run_tunnel(channel, request, ip)


@app.websocket(settings.WS_PATH + "/{anything:path}")
async def ws_endpoint_extra(ws: WebSocket, anything: str) -> None:
    await ws_endpoint(ws)


@app.post(settings.XHTTP_PATH + "/{session_id}/{seq}")
async def xhttp_up_packet_route(request: Request, session_id: str, seq: int):
    if xray_active():
        from .xray_engine import XHTTP_PORT

        return await _proxy_to_xray(request, XHTTP_PORT)
    return await xhttp_upload_packet(request, session_id, seq)


@app.post(settings.XHTTP_PATH + "/{session_id}")
async def xhttp_up_route(request: Request, session_id: str):
    if xray_active():
        from .xray_engine import XHTTP_PORT

        return await _proxy_to_xray(request, XHTTP_PORT)
    return await xhttp_upload(request, session_id)


@app.get(settings.XHTTP_PATH + "/{session_id}")
async def xhttp_down_route(request: Request, session_id: str):
    if xray_active():
        from .xray_engine import XHTTP_PORT

        return await _proxy_to_xray(request, XHTTP_PORT)
    return await xhttp_download(request, session_id)


# ───────────────────────────── سایت پوششی (catch-all) ─────────────────────────────
@app.get("/")
async def index():
    html, status = decoy.decoy_response("/")
    if not html:
        return JSONResponse({"status": "ok"})
    return HTMLResponse(html, status_code=status)


@app.api_route("/{path:path}", methods=["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, path: str):
    """هر مسیر ناشناخته → سایت پوششی (یا پاسخ ساده اگر decoy خاموش باشد)."""
    html, status = decoy.decoy_response("/" + path)
    if not html:
        return PlainTextResponse("", status_code=204)
    return HTMLResponse(html, status_code=status)
