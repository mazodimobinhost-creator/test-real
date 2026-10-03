"""سرویس نود: رله‌ی VLESS روی یک پورت واحد (همان چیزی که Railway می‌دهد)."""

from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from . import settings, sync, xhttp
from .policy import policy
from .relay import WsChannel, client_ip_from_headers, read_vless_request, run_tunnel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("mlp.node")

app = FastAPI(title="MLP Node", docs_url=None, redoc_url=None)
app.include_router(xhttp.router, prefix=settings.XHTTP_PATH, tags=["xhttp"])


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "node starting · name=%s panel=%s ws=%s xhttp=%s",
        settings.NODE_NAME,
        settings.PANEL_URL or "(unset)",
        settings.WS_PATH,
        settings.XHTTP_PATH,
    )
    asyncio.create_task(sync.sync_loop())
    asyncio.create_task(sync.report_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await sync.close()


@app.get("/healthz")
async def healthz():
    status = policy.status()
    status.update(
        {
            "ok": True,
            "service": "mlp-node",
            "role": "node",
            "panel_ok": sync.panel_ok(),
            "panel_error": sync.last_error(),
            "panel_url": settings.PANEL_URL,
        }
    )
    return JSONResponse(status)


@app.get("/", response_class=HTMLResponse)
async def index():
    status = policy.status()
    return HTMLResponse(
        f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>MLP Node · {settings.NODE_NAME}</title>
<style>body{{background:#0b1020;color:#eaf0ff;font-family:Tahoma;direction:rtl;padding:40px}}
code{{background:#141a2f;padding:2px 6px;border-radius:6px}}</style></head><body>
<h2>{settings.NODE_FLAG} نود {settings.NODE_NAME}</h2>
<p>این سرویس یک نود رله است. کلاینت‌ها از طریق کانفیگ اشتراک به آن وصل می‌شوند.</p>
<ul>
<li>مسیر WS: <code>{settings.WS_PATH}</code></li>
<li>مسیر XHTTP: <code>{settings.XHTTP_PATH}</code></li>
<li>کاربران فعال روی این نود: <b>{status['clients']}</b></li>
<li>وضعیت اتصال به پنل: <b>{'✅ متصل' if sync.panel_ok() else '❌ قطع'}</b>
    {'<small>(' + sync.last_error() + ')</small>' if sync.last_error() else ''}</li>
</ul></body></html>"""
    )


def _client_ip(ws: WebSocket) -> str:
    return client_ip_from_headers(dict(ws.headers), ws.client.host if ws.client else "?")


@app.websocket(settings.WS_PATH)
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    ip = _client_ip(ws)
    channel = WsChannel(ws)
    try:
        request = await read_vless_request(channel, max_wait=30.0)
    except Exception as exc:
        policy.push_event(f"هدر نامعتبر از {ip}: {type(exc).__name__}", "warn")
        try:
            await ws.close(code=1008)
        except Exception:
            pass
        return
    await run_tunnel(channel, request, ip)


@app.websocket(settings.WS_PATH + "/{anything:path}")
async def ws_endpoint_extra(ws: WebSocket, anything: str) -> None:
    await ws_endpoint(ws)


@app.get(settings.WS_PATH, response_class=PlainTextResponse)
async def ws_probe():
    """اگر مرورگر یا healthcheck روی مسیر WS بیاید."""
    return PlainTextResponse("MLP node is running. WebSocket endpoint for VLESS clients only.", status_code=400)


@app.get("/sub/{token}")
async def sub_passthrough(token: str, request: Request):
    """پروکسی صفحه‌ی اشتراک از پنل (برای وقتی دامنه‌ی پنل فیلتر است)."""
    if not settings.PANEL_URL:
        return JSONResponse({"ok": False, "error": "panel url not configured"}, status_code=502)
    sub_path = "sub"
    url = f"{settings.PANEL_URL}/{sub_path}/{token}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                params=dict(request.query_params),
                headers={
                    "User-Agent": request.headers.get("user-agent", ""),
                    "Accept": request.headers.get("accept", ""),
                },
            )
        content_type = resp.headers.get("content-type", "text/plain; charset=utf-8")
        return Response(content=resp.content, media_type=content_type, status_code=resp.status_code)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"{type(exc).__name__}"}, status_code=502)


@app.get("/info")
async def info():
    return {
        "ok": True,
        "service": "mlp-node",
        "version": settings.APP_VERSION,
        "name": settings.NODE_NAME,
        "flag": settings.NODE_FLAG,
        "ws_path": settings.WS_PATH,
        "xhttp_path": settings.XHTTP_PATH,
        "users": len(policy.users),
        "panel_ok": sync.panel_ok(),
    }
