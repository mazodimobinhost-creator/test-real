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
sys.path.insert(0, str(ROOT))


def json_dumps(obj) -> str:
    import json as _json

    return _json.dumps(obj, ensure_ascii=False)
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
            "MLP_DECOY": "auto",
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
    _, hz_plain = await http_json(f"http://127.0.0.1:{NODE_PORT}/healthz")
    _, hz = await http_json(f"http://127.0.0.1:{NODE_PORT}/healthz?key={token}")
    check(hz_plain == {"status": "ok"}, "پاسخ عمومی /healthz بی‌اثر است")
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
    _, hz_client = await http_json(f"http://127.0.0.1:{NODE_PORT}/healthz?key={token}")
    check(int(hz_client.get("clients") or 0) >= 1, "کاربر روی نود دیده شد", f"clients={hz_client.get('clients')}")

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


    # ── سایت عمومی (پوششی) و صفحات ──
    print(f"{YELLOW}==> تست سایت عمومی و صفحات{RESET}")
    import httpx as _httpx2

    async with _httpx2.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        home = await client.get(f"http://127.0.0.1:{PANEL_PORT}/")
        pages = {}
        for path in ("/plans", "/status", "/download", "/contact", "/api/site", "/robots.txt", "/sitemap.xml"):
            pages[path] = await client.get(f"http://127.0.0.1:{PANEL_PORT}{path}")
        unknown = await client.get(f"http://127.0.0.1:{PANEL_PORT}/this-page-does-not-exist")
        go = await client.get(f"http://127.0.0.1:{PANEL_PORT}/go")
        node_home = await client.get(f"http://127.0.0.1:{NODE_PORT}/")
        node_inner = await client.get(f"http://127.0.0.1:{NODE_PORT}/about?ref=nav")
        node_missing = await client.get(f"http://127.0.0.1:{NODE_PORT}/no-such-path")
        node_cfg = await client.get(f"http://127.0.0.1:{NODE_PORT}/_mlp/config.js")
        hz_public = await client.get(f"http://127.0.0.1:{NODE_PORT}/healthz")
        hz_private = await client.get(f"http://127.0.0.1:{NODE_PORT}/healthz?key={token}")

    import sqlite3  # noqa: E402

    _db = sqlite3.connect(str(data_dir / "mlp.sqlite3"))
    secret = _db.execute("SELECT value FROM settings WHERE key='secret_path'").fetchone()[0]
    _db.close()
    check(home.status_code == 200 and "<html" in home.text.lower(), "صفحه‌ی اصلی سایت عمومی")
    check(all(r.status_code == 200 for r in pages.values()),
          "همه‌ی صفحات سایت و sitemap/robots", ",".join(f"{k}:{v.status_code}" for k, v in pages.items()))
    check("تعرفه" in pages["/plans"].text or "plan" in pages["/plans"].text.lower(),
          "صفحه تعرفه‌ها محتوا دارد")
    check(unknown.status_code == 404 and "<html" in unknown.text.lower(), "مسیر ناشناخته → صفحه ۴۰۴ سایت")
    check(go.status_code in (302, 307) and go.headers.get("location") == secret, "میان‌بر /go به مسیر مخفی پنل")
    check(hz_public.status_code == 200 and hz_public.json() == {"status": "ok"},
          "نود بدون کلید اطلاعات لو نمی‌دهد")
    check(hz_private.status_code == 200 and hz_private.json().get("role") == "node",
          "نود با کلید وضعیت کامل می‌دهد")
    check(node_cfg.status_code == 200 and "__APP_CONFIG__" in node_cfg.text, "فایل پیکربندی سایت پوششی نود")

    # سایت پوششی نود نباید شبیه پروکسی باشد
    body = node_home.text if node_home.status_code == 200 else ""
    looks_like_site = (
        node_home.status_code == 200
        and "<html" in body.lower()
        and not any(word in body.lower() for word in ("vless", "uuid", "panel", "xray", "subscription"))
        and ("<!doctype html>" in body.lower() or "<html" in body.lower())
    )
    check(looks_like_site, "نود سایت پوششی واقعی نشان می‌دهد (بدون اثری از پروکسی)",
          f"len={len(body)} kind={os.environ.get('MLP_DECOY', 'auto')}")
    check(node_inner.status_code == 200 and len(node_inner.text) > 500, "مسیر داخلی سایت پوششی هم پاسخ می‌دهد")
    check(node_missing.status_code == 404 and "<html" in node_missing.text.lower(), "۴۰۴ سایت پوششی نود")

    # دو نود با نام‌های مختلف نباید سایت یکسان داشته باشند (انتخاب پایدار از نام)
    from node.app import decoy as node_decoy  # noqa: E402

    _prev_env = {k: os.environ.get(k) for k in ("MLP_DECOY", "MLP_NODE_NAME", "RAILWAY_PUBLIC_DOMAIN")}
    try:
        os.environ["MLP_DECOY"] = "shop"
        forced_shop = node_decoy.choose_kind()
        os.environ["MLP_DECOY"] = "blog"
        forced_blog = node_decoy.choose_kind()
        os.environ["MLP_DECOY"] = "none"
        forced_none = node_decoy.choose_kind()
        os.environ.pop("MLP_DECOY", None)
        os.environ["MLP_NODE_NAME"] = "NodeA"
        a1, a2 = node_decoy.choose_kind(), node_decoy.choose_kind()
        os.environ["MLP_NODE_NAME"] = "NodeB"
        b1 = node_decoy.choose_kind()
    finally:
        for k, v in _prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    check((forced_shop, forced_blog, forced_none) == ("shop", "blog", "none"), "انتخاب دستی سایت پوششی (shop/blog/none)")
    check(a1 == a2 and a1 in node_decoy.SITE_KINDS, "انتخاب سایت پوششی پایدار بر اساس نام نود", a1)
    check(b1 in node_decoy.SITE_KINDS, "نام دیگر نود هم سایت معتبر می‌سازد", b1)

    # ── برند اختصاصی ──
    print(f"{YELLOW}==> تست برند و ظاهر اختصاصی{RESET}")
    brand_name = "آزمایش‌سرا"
    resp, brand_resp = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/settings", "POST",
        {"brand_name": brand_name, "brand_slogan": "شعار تست", "brand_hero": "تیتر تست",
         "brand_features": "ویژگی یک\nویژگی دو", "brand_color": "#12b8a6", "brand_color2": "#ff7a59"},
        cookies,
    )
    async with _httpx2.AsyncClient(timeout=15.0) as client:
        home2 = await client.get(f"http://127.0.0.1:{PANEL_PORT}/")
        site2 = await client.get(f"http://127.0.0.1:{PANEL_PORT}/api/site")
    check(resp.status_code == 200 and brand_name in home2.text, "نام برند روی سایت عمومی اعمال شد")
    check("#12b8a6" in home2.text, "رنگ اختصاصی برند در CSS سایت")
    check(brand_name in site2.text and "تیتر تست" in site2.text, "API سایت برند را برمی‌گرداند")

    # ── اعلان‌ها ──
    resp, ann = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/announcements", "POST",
        {"title": "خبر مهم", "body": "امشب بروزرسانی داریم", "level": "warn", "enabled": True}, cookies,
    )
    ann_id = (ann.get("announcement") or {}).get("id")
    await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/settings", "POST", {"announce_bar": "۱۰٪ تخفیف"}, cookies)
    async with _httpx2.AsyncClient(timeout=15.0) as client:
        home3 = await client.get(f"http://127.0.0.1:{PANEL_PORT}/")
    check(bool(ann_id) and "خبر مهم" in home3.text, "اعلان در سایت عمومی دیده می‌شود")
    check("۱۰٪ تخفیف" in home3.text, "نوار اعلان بالای سایت")
    _, anns = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/announcements", cookies=cookies)
    check(any(a["id"] == ann_id for a in anns.get("announcements", [])), "اعلان در API پنل هست")

    # ── حالت‌های سایت ──
    await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/settings", "POST", {"site_mode": "countdown"}, cookies)
    async with _httpx2.AsyncClient(timeout=15.0) as client:
        cd = await client.get(f"http://127.0.0.1:{PANEL_PORT}/")
        cd_unknown = await client.get(f"http://127.0.0.1:{PANEL_PORT}/some-random")
    check("به‌زودی برمی‌گردیم" in cd.text and cd_unknown.status_code == 200, "حالت «به‌زودی» سایت")
    await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/settings", "POST", {"site_mode": "marketing"}, cookies)

    # ── رزیلر و کیف پول ──
    print(f"{YELLOW}==> تست رزیلر و کیف پول{RESET}")
    resp, rs = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/resellers", "POST",
        {"name": "رزیلر تست", "username": "reseller1", "password": "pass123", "price_gb": 1500,
         "price_day": 200, "min_gb": 1, "note": "5551234"}, cookies,
    )
    reseller = rs.get("reseller") or {}
    check(resp.status_code == 200 and reseller.get("id") and "password_hash" not in reseller,
          "ساخت رزیلر (بدون افشای رمز)")
    r_id = reseller.get("id")
    resp, top = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/resellers/topup", "POST",
        {"reseller_id": r_id, "amount": 500000, "note": "شارژ دستی"}, cookies,
    )
    check(resp.status_code == 200 and (top.get("balance") or 0) == 500000, "شارژ کیف پول رزیلر", f"balance={top.get('balance')}")
    _, wl = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/wallet", cookies=cookies)
    check(any(t["status"] == "approved" and t["amount"] == 500000 for t in wl.get("txs", [])), "تراکنش در دفتر کیف پول")

    # رزیلر با موجودی کم نمی‌تواند خرید کند
    from panel.app.bot import _reseller_buy_plan  # noqa: E402

    resp, plan = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/plans", "POST",
        {"name": "پلن رزیلری", "traffic_gb": 10, "days": 30, "price": "۲۰۰ هزار", "reseller_price": 0,
         "max_ips": 0, "speed_kbps": 0, "enabled": True}, cookies,
    )
    plan_id = (plan.get("plan") or {}).get("id")
    computed = 10 * int(reseller["price_gb"]) + 30 * int(reseller["price_day"])
    check(computed == 21000, "قیمت‌گذاری خودکار رزیلر (حجم/روز)", f"{computed:,} تومان")
    _, users_before = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/users", cookies=cookies)
    rs_row = [r for r in (await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/resellers", cookies=cookies))[1]["resellers"]
              if r["id"] == r_id][0]
    await _reseller_buy_plan(999999, dict(rs_row, balance=100), plan_id)   # موجودی کم → نباید کاربر بسازد
    _, users_after = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/users", cookies=cookies)
    check(len(users_after.get("users", [])) == len(users_before.get("users", [])),
          "رزیلر بدون موجودی کافی کاربر نمی‌سازد")

    # کاربر زیرمجموعه رزیلر در پنل دیده شود
    resp, ruser = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/users", "POST",
        {"name": "کاربر رزیلر", "limit_gb": 2, "days": 30, "reseller_id": r_id, "enabled": True}, cookies,
    )
    r_user = ruser.get("user") or {}
    _, ulist = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/users", cookies=cookies)
    row = [u for u in ulist.get("users", []) if u["id"] == r_user.get("id")]
    check(bool(row) and row[0].get("reseller_name") == "رزیلر تست", "کاربر رزیلر با نام رزیلر در پنل")

    # ── مسیر ساب اختصاصی ──
    print(f"{YELLOW}==> تست مسیر ساب و دامنه{RESET}")
    import base64  # noqa: E402

    tok = r_user.get("sub_token", "")
    async with _httpx2.AsyncClient(timeout=15.0) as client:
        sub_a = await client.get(f"http://127.0.0.1:{PANEL_PORT}/sub/{tok}", headers={"User-Agent": "v2rayNG/1.8"})
        sub_stats = await client.get(f"http://127.0.0.1:{PANEL_PORT}/sub/{tok}?stats=1")
        sub_html = await client.get(f"http://127.0.0.1:{PANEL_PORT}/sub/{tok}",
                                    headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    check(sub_a.status_code == 200 and "vless://" in base64.b64decode(sub_a.text + "===").decode("utf-8", "replace"),
          "لینک ساب base64 سالم")
    stats_json = sub_stats.json() if sub_stats.status_code == 200 else {}
    check(stats_json.get("ok") is True and stats_json.get("name") == "کاربر رزیلر"
          and stats_json.get("status_fa") in ("فعال", "غیرفعال", "منقضی", "اتمام حجم"),
          "ساب با ?stats=1 اطلاعات JSON می‌دهد", str(stats_json.get("status_fa", "")))
    check(sub_html.status_code == 200 and "اشتراک" in sub_html.text, "صفحه HTML ساب در مرورگر")

    # ── آموزش راه‌اندازی ──
    print(f"{YELLOW}==> تست آموزش راه‌اندازی{RESET}")
    _, tut = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/tutorial", cookies=cookies)
    steps = tut.get("steps", [])
    files = tut.get("files", {})
    check(len(steps) >= 7 and all(s.get("code") for s in steps), "آموزش گام‌به‌گام داخل پنل", f"{len(steps)} گام")
    check(len(files) >= 10 and any("Dockerfile.xray" in k for k in files),
          "فایل‌های راه‌اندازی برای دانلود آماده‌اند", f"{len(files)} فایل")
    check("MLP_NODE_TOKEN" in files.get("node/.env.example", "") or "MLP_NODE_TOKEN" in files.get("node/Dockerfile", ""),
          "نمونه متغیرهای نود در بسته آموزش")
    resp, _ = await http_json(
        f"http://127.0.0.1:{PANEL_PORT}/api/admin/tutorial", "POST",
        {"key": "step_panel", "title": "عنوان ویرایش‌شده", "text": "متن دلخواه"}, cookies,
    )
    _, tut2 = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/tutorial", cookies=cookies)
    edited = [s for s in tut2.get("steps", []) if s["key"] == "step_panel"][0]
    check(resp.status_code == 200 and edited["title"] == "عنوان ویرایش‌شده", "ویرایش متن آموزش از داخل پنل")
    await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/tutorial", "POST",
                    {"key": "step_panel", "reset": True}, cookies)
    _, tut3 = await http_json(f"http://127.0.0.1:{PANEL_PORT}/api/admin/tutorial", cookies=cookies)
    reset_step = [s for s in tut3.get("steps", []) if s["key"] == "step_panel"][0]
    check(reset_step["title"] != "عنوان ویرایش‌شده", "بازگردانی آموزش به پیش‌فرض")

    # ── رابط کاربری پنل ──
    print(f"{YELLOW}==> تست رابط کاربری اختصاصی{RESET}")
    async with _httpx2.AsyncClient(timeout=15.0, cookies=dict(cookies)) as client:
        panel_ui = await client.get(f"http://127.0.0.1:{PANEL_PORT}{secret}")
        login_ui = await client.get(f"http://127.0.0.1:{PANEL_PORT}{secret}?fresh=1")
    html_ui = panel_ui.text
    tabs = ["داشبورد", "لوکیشن‌ها", "کاربران", "پلن‌ها", "سفارش‌ها", "رزیلرها", "کیف پول",
            "اعلان‌ها", "برند و ظاهر", "آموزش راه‌اندازی", "رویدادها", "تنظیمات"]
    check(panel_ui.status_code == 200 and all(t in html_ui for t in tabs), "همه‌ی تب‌های پنل در رابط کاربری", f"{len(tabs)} تب")
    check("آموزش راه‌اندازی" in html_ui and "dlFile" in html_ui and "download(" in html_ui,
          "دانلود فایل‌ها و آموزش داخل UI")
    check("__ADMIN_PATH__" not in html_ui and "Momentum" not in html_ui,
          "قالب UI پس از جای‌گذاری متغیرها سالم است")
    check(html_ui.count("<html") == 1 and html_ui.count("/api/admin/") >= 10 and "async function go(" in html_ui,
          "UI یک سند مستقل با API‌های واقعی", f"api_refs={html_ui.count('/api/admin/')}")

    # ── موتور Xray (بدون باینری → config-only) ──
    print(f"{YELLOW}==> تست موتور Xray (حالت پیکربندی){RESET}")
    from node.app.xray_engine import engine as xray_engine  # noqa: E402

    selfcheck = xray_engine.self_check()
    check(selfcheck.get("ok") and selfcheck.get("clients") == 0 and len(selfcheck.get("inbounds", [])) >= 3,
          "پیکربندی Xray ساخته می‌شود", f"{selfcheck.get('bytes')} بایت · {','.join(selfcheck.get('inbounds', []))}")
    cfg_path = Path(selfcheck["path"]) if selfcheck.get("path") else None
    cfg_text = cfg_path.read_text(encoding="utf-8") if cfg_path and cfg_path.exists() else json_dumps(selfcheck.get("config", {}))
    check("10085" in cfg_text and '"stats"' in cfg_text and "bittorrent" in cfg_text.lower(),
          "Xray: API آماری ۱۰۰۸۵ + بلاک تورنت")
    check("splithttp" in cfg_text or "xhttp" in cfg_text, "Xray: ترابرد XHTTP در پیکربندی")
    if not selfcheck.get("binary_found"):
        check(xray_engine.status().get("running") is False, "نبود باینری Xray → اجرا نمی‌شود (fallback)")

    # پروکسی نود در حالت پایتون بدون باینری سرِ جایش است
    from node.app.main import xray_active  # noqa: E402

    check(xray_active() is False, "نود بدون باینری روی موتور پایتون می‌ماند")

    # ── فایل‌های استقرار Xray ──
    check((ROOT / "node" / "nginx.conf.template").exists() and (ROOT / "node" / "start-xray.sh").exists(),
          "فایل‌های nginx و اسکریپت راه‌اندازی Xray موجودند")
    nginx_conf = (ROOT / "node" / "nginx.conf.template").read_text(encoding="utf-8")
    check("proxy_pass http://127.0.0.1:${XRAY_WS_PORT}" in nginx_conf and "proxy_buffering off" in nginx_conf,
          "nginx: مسیر WS به Xray با بافر خاموش")
    docker_xray = (ROOT / "node" / "Dockerfile.xray").read_text(encoding="utf-8")
    check("Xray-linux-64.zip" in docker_xray and "MLP_ENGINE=xray" in docker_xray,
          "Dockerfile.xray باینری را از انتشار رسمی می‌گیرد")

    # ── بررسی هم‌خوانی بسته‌ی فایل‌های آموزش ──
    import subprocess as _sp

    gen = _sp.run([PY, str(ROOT / "tools" / "gen_setup_files.py"), "--check"], cwd=ROOT, capture_output=True, text=True)
    check(gen.returncode == 0, "بسته setup_files.json با مخزن هم‌خوان است", gen.stdout.strip() or gen.stderr.strip()[:80])

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
