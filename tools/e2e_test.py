#!/usr/bin/env python3
"""تست سرتاسری محلی: پنل + نود + یک کلاینت واقعی VLESS روی WebSocket.

اجرا:
    python3 tools/e2e_test.py

این اسکریپت دو سرویس را بالا می‌آورد، یک لوکیشن و کاربر می‌سازد، از طریق تونل
یک درخواست HTTP واقعی می‌فرستد، محدودیت حجم را آزمایش می‌کند و در پایان
گزارش مصرف را از API پنل می‌خواند.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid as uuid_lib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
VENV_PY = Path("/tmp/venv/bin/python")
if VENV_PY.exists():
    PY = str(VENV_PY)

PANEL_PORT = 0   # در زمان اجرا انتخاب می‌شود
NODE_PORT = 0

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, extra: str = "") -> None:
    results.append((ok, label))
    mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{mark}] {label}{(' · ' + extra) if extra else ''}")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port: int, timeout: float = 45.0, proc: subprocess.Popen | None = None) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if proc and proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.6):
                return True
        except OSError:
            time.sleep(0.3)
    return False


async def http_json(url: str, method: str = "GET", body: dict | None = None, cookies: dict | None = None):
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(method, url, json=body, cookies=cookies, follow_redirects=False)
        try:
            data = resp.json()
        except Exception:
            data = {}
        return resp, data


def build_vless_header(uid: str, host: str, port: int, command: int = 1) -> bytes:
    raw = uuid_lib.UUID(uid).bytes
    out = bytearray()
    out.append(0)  # version
    out += raw
    out.append(0)  # addon length
    out.append(command)
    out += port.to_bytes(2, "big")
    if ":" in host:
        out.append(3)
        out += socket.inet_pton(socket.AF_INET6, host)
    else:
        try:
            socket.inet_aton(host)
            out.append(1)
            out += socket.inet_aton(host)
        except OSError:
            out.append(2)
            data = host.encode()
            out.append(len(data))
            out += data
    return bytes(out)


async def vless_ws_request(uuid_str: str, target_host: str, target_port: int, payload: bytes, timeout: float = 12.0):
    """یک درخواست از داخل تونل: هدر VLESS + payload؛ پاسخ را برمی‌گرداند."""
    import websockets

    uri = f"ws://127.0.0.1:{NODE_PORT}/ws"
    async with websockets.connect(uri, max_size=None, open_timeout=8) as ws:
        await ws.send(build_vless_header(uuid_str, target_host, target_port) + payload)
        chunks = []
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                if isinstance(msg, str):
                    msg = msg.encode()
                chunks.append(msg)
                if sum(len(c) for c in chunks) > 4096:
                    break
        except (asyncio.TimeoutError, Exception):
            pass
    return b"".join(chunks)


async def main() -> int:
    global PANEL_PORT, NODE_PORT
    PANEL_PORT = free_port()
    NODE_PORT = free_port()
    data_dir = Path("/tmp/mlp-e2e")
    shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    panel_env = os.environ.copy()
    panel_env.update(
        {
            "MLP_DATA_DIR": str(data_dir),
            "PORT": str(PANEL_PORT),
            "MLP_ADMIN_PASSWORD": "admin",
            "MLP_PUBLIC_URL": f"http://127.0.0.1:{PANEL_PORT}",
        }
    )
    print(f"{YELLOW}==> اجرای پنل روی پورت {PANEL_PORT}{RESET}")
    panel_log = open(data_dir / "panel.log", "w")
    panel = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PANEL_PORT), "--log-level", "warning"],
        cwd=ROOT / "panel",
        env=panel_env,
        stdout=panel_log,
        stderr=subprocess.STDOUT,
    )
    if not wait_port(PANEL_PORT, 45, panel):
        print(f"{RED}پنل بالا نیامد؛ لاگ:{RESET}")
        print((data_dir / "panel.log").read_text()[-3000:])
        panel.kill()
        return 1
    check(True, "پنل بالا آمد")

    # ── ورود ادمین ──
    resp, _ = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/login", "POST", {"username": "admin", "password": "admin"}
    )
    sid = resp.cookies.get("mlp_sid")
    check(resp.status_code == 200 and bool(sid), "ورود ادمین")
    cookies = {"mlp_sid": sid}

    # ── ساخت لوکیشن ──
    resp, loc = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/locations",
        "POST",
        {
            "name": "LocalTest",
            "flag": "🧪",
            "region": "local",
            "host": f"127.0.0.1:{NODE_PORT}",
            "transports": ["ws", "xhttp"],
            "ws_path": "/ws",
            "xhttp_path": "/xhttp",
        },
        cookies,
    )
    location = loc.get("location") or {}
    env_snippet = loc.get("env") or ""
    token = ""
    for line in env_snippet.splitlines():
        if line.startswith("MLP_NODE_TOKEN="):
            token = line.split("=", 1)[1]
    check(resp.status_code == 200 and bool(token), "ساخت لوکیشن + توکن نود", location.get("name", ""))

    # ── اجرای نود ──
    node_env = os.environ.copy()
    node_env.update(
        {
            "MLP_PANEL_URL": f"http://127.0.0.1:{PANEL_PORT}",
            "MLP_NODE_TOKEN": token,
            "MLP_NODE_NAME": "LocalTest",
            "MLP_WS_PATH": "/ws",
            "MLP_XHTTP_PATH": "/xhttp",
            "MLP_SYNC_INTERVAL": "3",
            "MLP_REPORT_INTERVAL": "3",
            "PORT": str(NODE_PORT),
        }
    )
    print(f"{YELLOW}==> اجرای نود روی پورت {NODE_PORT}{RESET}")
    node_log = open(data_dir / "node.log", "w")
    node = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(NODE_PORT), "--log-level", "warning"],
        cwd=ROOT / "node",
        env=node_env,
        stdout=node_log,
        stderr=subprocess.STDOUT,
    )
    if not wait_port(NODE_PORT, 45, node):
        print(f"{RED}نود بالا نیامد؛ لاگ:{RESET}")
        print((data_dir / "node.log").read_text()[-3000:])
        panel.kill()
        node.kill()
        return 1
    check(True, "نود بالا آمد")

    await asyncio.sleep(5)  # اولین sync

    # ── وضعیت اتصال نود به پنل ──
    _, hz = await http_json(f"http://127.0.0.1:{NODE_PORT}/healthz")
    check(bool(hz.get("panel_ok")), "نود با توکن به پنل وصل شد", f"users={hz.get('clients')}")

    # ── ساخت کاربر ──
    resp, user_resp = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/users",
        "POST",
        {"name": "e2e-user", "limit_gb": 1, "days": 30, "max_ips": 0, "speed_kbps": 0, "enabled": True},
        cookies,
    )
    user = user_resp.get("user") or {}
    check(resp.status_code == 200 and bool(user.get("uuid")), "ساخت کاربر", user.get("name", ""))

    await asyncio.sleep(5)  # sync دوم تا کاربر روی نود بیاید
    _, hz = await http_json(f"http://127.0.0.1:{NODE_PORT}/healthz")
    check(int(hz.get("clients") or 0) >= 1, "کاربر روی نود دیده شد", f"clients={hz.get('clients')}")

    # ── تست واقعی تونل ──
    # مقصد تست: خود پنل روی 127.0.0.1 (در سندباکس دسترسی به اینترنت بیرونی بسته است)
    target_host = os.environ.get("MLP_TEST_TARGET", "127.0.0.1")
    target_port = int(os.environ.get("MLP_TEST_PORT", str(PANEL_PORT)))
    payload = f"GET /healthz HTTP/1.1\r\nHost: {target_host}:{target_port}\r\nUser-Agent: mlp-e2e\r\nConnection: close\r\n\r\n".encode()
    print(f"{YELLOW}==> تست تونل VLESS → {target_host}:{target_port}{RESET}")
    raw = await vless_ws_request(user["uuid"], target_host, target_port, payload)
    has_header = raw[:2] == b"\x00\x00"
    text = raw[2:].decode("utf-8", "replace") if has_header else raw.decode("utf-8", "replace")
    check(has_header, "هدر پاسخ VLESS (دو بایت اول) درست است")
    check("HTTP/" in text.split("\r\n")[0] if text else False, "داده از تونل برگشت", text.split("\r\n")[0][:60] if text else "بدون پاسخ")

    # ── تست مجوز: UUID ناشناس رد شود ──
    fake = str(uuid_lib.uuid4())
    raw_fake = await vless_ws_request(fake, target_host, target_port, payload, timeout=4)
    check(len(raw_fake) == 0, "UUID ناشناس رد می‌شود")

    # ── تست ساب ──
    sub_url = f"http://127.0.0.1:{PANEL_PORT}/sub/{user['sub_token']}"
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        base64_resp = await client.get(sub_url, headers={"User-Agent": "v2rayNG/1.8"})
        browser_resp = await client.get(sub_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    import base64 as b64

    decoded = ""
    try:
        decoded = b64.b64decode(base64_resp.text + "===").decode("utf-8", "replace")
    except Exception:
        pass
    check("vless://" in decoded and "127.0.0.1" in decoded, "ساب base64 برای کلاینت درست است")
    check("http" in browser_resp.text and len(browser_resp.text) > 1500 and "اشتراک" in browser_resp.text, "صفحه HTML ساب برای مرورگر")

    # ── گزارش مصرف ──
    await asyncio.sleep(6)
    _, users = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/users", cookies=cookies)
    me = next((u for u in users.get("users", []) if u["id"] == user["id"]), {})
    check(int(me.get("used_bytes") or 0) > 0, "مصرف روی پنل ثبت شد", f"used={me.get('used_bytes')}")
    _, overview = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/overview", cookies=cookies)
    locs = overview.get("locations", [])
    check(any(l["id"] == location["id"] and l["online"] for l in locs), "پنل لوکیشن را آنلاین می‌بیند")

    # ── تست قطع کاربر (غیرفعال‌سازی از پنل) ──
    await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/users",
        "POST",
        {"id": user["id"], "name": "e2e-off", "limit_gb": 1, "days": 30, "enabled": False},
        cookies,
    )
    await asyncio.sleep(6)
    raw_off = await vless_ws_request(user["uuid"], target_host, target_port, payload, timeout=5)
    check(len(raw_off) == 0, "کاربر غیرفعال‌شده از پنل قطع می‌شود")

    # ── تست منطق کوتا / IP / انقضا به‌صورت واحد ──
    sys.path.insert(0, str(ROOT / "node"))
    from app.policy import Policy  # noqa: E402

    p1 = Policy()
    p1.apply_bundle({"users": [{"uuid": "u1", "enabled": 1, "limit_bytes": 100, "used_bytes": 0, "expire_at": 0, "max_ips": 0, "speed_kbps": 0}]})
    a1 = p1.allow("u1")[0]
    p1.note("u1", 60)
    a2 = p1.allow("u1")[0]
    p1.note("u1", 50)
    a3 = p1.allow("u1")[0]
    check(a1 and a2 and (not a3), "کوتا: بعد از عبور از سقف رد می‌شود")

    p2 = Policy()
    p2.apply_bundle({"users": [{"uuid": "u2", "enabled": 1, "limit_bytes": 0, "used_bytes": 0, "expire_at": 0, "max_ips": 1, "speed_kbps": 0}]})
    ip1 = p2.check_ip("u2", "1.1.1.1")
    ip2 = p2.check_ip("u2", "2.2.2.2")
    check(ip1 and (not ip2), "محدودیت IP هم‌زمان اعمال می‌شود")

    p3 = Policy()
    p3.apply_bundle({"users": [{"uuid": "u3", "enabled": 1, "limit_bytes": 0, "used_bytes": 0, "expire_at": 1, "max_ips": 0, "speed_kbps": 0}]})
    check(not p3.allow("u3")[0], "کاربر منقضی رد می‌شود")

    p4 = Policy()
    p4.apply_bundle({"users": [{"uuid": "u4", "enabled": 1, "limit_bytes": 0, "used_bytes": 0, "expire_at": 0, "max_ips": 0, "speed_kbps": 64}]})
    t0 = time.time()
    await p4.throttle("u4", 64 * 1024)
    elapsed = time.time() - t0
    check(elapsed >= 4.0, "محدودیت سرعت (64kbps → حدود ۸ ثانیه برای ۶۴KB)", f"{elapsed:.1f}s")

    # ── تست XHTTP ──
    print(f"{YELLOW}==> تست ترابرد XHTTP{RESET}")
    try:
        import httpx as _httpx

        session_id = uuid_lib.uuid4().hex
        header = build_vless_header(user["uuid"], target_host, target_port)
        # کاربر محدود شده؛ دوباره حجمش را زیاد می‌کنیم
        await http_json(
            f"http://127.0.0.1:{PANEL_PORT}/api/admin/users",
            "POST",
            {"id": user["id"], "name": "e2e-limited", "limit_gb": 1, "days": 30, "enabled": True},
            cookies,
        )
        await asyncio.sleep(6)
        got = b""

        async with _httpx.AsyncClient(timeout=15.0) as client:
            async def downlink():
                nonlocal got
                async with client.stream(
                    "GET", f"http://127.0.0.1:{NODE_PORT}/xhttp/{session_id}", headers={"User-Agent": "xray"}
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        got += chunk
                        if len(got) > 512:
                            break

            task = asyncio.create_task(downlink())
            await asyncio.sleep(0.5)
            await client.post(
                f"http://127.0.0.1:{NODE_PORT}/xhttp/{session_id}",
                content=header + payload,
                headers={"User-Agent": "xray"},
            )
            try:
                await asyncio.wait_for(task, timeout=8)
            except asyncio.TimeoutError:
                task.cancel()
        text_x = got[2:].decode("utf-8", "replace") if got[:2] == b"\x00\x00" else got.decode("utf-8", "replace")
        check("HTTP/" in text_x, "تونل XHTTP داده برگرداند", text_x.split("\r\n")[0][:50] if text_x else "بدون پاسخ")
    except Exception as exc:
        check(False, "تونل XHTTP", f"{type(exc).__name__}: {exc}")

    # ── پاکسازی ──
    for proc in (node, panel):
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=8)
        except Exception:
            proc.kill()

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print(f"\n{YELLOW}نتیجه: {passed}/{total} تست موفق{RESET}")
    if passed != total:
        print(f"{YELLOW}--- لاگ نود ---{RESET}")
        print((data_dir / "node.log").read_text()[-2500:])
        print(f"{YELLOW}--- لاگ پنل ---{RESET}")
        print((data_dir / "panel.log").read_text()[-2500:])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
