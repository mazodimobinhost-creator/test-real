"""اسکنر: پیدا کردن آی‌پی/هاست تمیز و سریع برای هر لوکیشن.

کاربردهای اصلی:
* انتخاب **آی‌پی تمیز** (Clean IP) برای دامنه‌های Cloudflare/لوکیشن‌ها
* بررسی سالم بودن **پروکسی IP**ها و سرورهای بالادستی (تانل)

هر کاندید: چند بار TCP connect (+ TLS) و اندازه‌گیری تأخیر و پایداری.
بدون هیچ درخواست سنگین؛ کاملاً موازی و با محدودسازی نرخ تا خودمان اذیت نشویم.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import ssl
import time

import httpx


def _normalize(target: str, default_port: int) -> tuple[str, int]:
    raw = (target or "").strip()
    if not raw:
        return "", default_port
    if raw.startswith("["):
        host, _, rest = raw[1:].partition("]")
        return host, int(rest.lstrip(":") or default_port)
    if raw.count(":") == 1 and "/" not in raw:
        host, _, port = raw.partition(":")
        return host, int(port or default_port)
    return raw, default_port


async def _probe(host: str, port: int, use_tls: bool, timeout: float, sni: str = "") -> tuple[bool, float, str]:
    started = time.perf_counter()
    writer = None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        if use_tls:
            ctx = ssl.create_default_context()
            await asyncio.wait_for(
                writer.start_tls(ctx, server_hostname=sni or host), timeout=timeout
            )
        latency = (time.perf_counter() - started) * 1000
        return True, latency, ""
    except Exception as exc:
        return False, (time.perf_counter() - started) * 1000, f"{type(exc).__name__}: {exc}"[:120]
    finally:
        if writer is not None:
            with contextlib.suppress(Exception):
                writer.close()


async def scan(
    targets: list[str],
    *,
    port: int = 443,
    use_tls: bool = True,
    attempts: int = 3,
    timeout: float = 3.0,
    concurrency: int = 32,
    sni: str = "",
) -> dict:
    """اسکن لیستی از هاست/آی‌پی و برگرداندن نتیجه‌ی مرتب‌شده بر اساس تأخیر."""
    sem = asyncio.Semaphore(max(1, min(128, concurrency)))
    results: list[dict] = []

    async def worker(target: str) -> None:
        host, host_port = _normalize(target, port)
        if not host:
            return
        async with sem:
            ok_count = 0
            latencies: list[float] = []
            last_error = ""
            for _ in range(max(1, attempts)):
                ok, latency, error = await _probe(host, host_port, use_tls, timeout, sni)
                if ok:
                    ok_count += 1
                    latencies.append(latency)
                else:
                    last_error = error
            avg = sum(latencies) / len(latencies) if latencies else 0.0
            best = min(latencies) if latencies else 0.0
            results.append({
                "target": target.strip(),
                "host": host,
                "port": host_port,
                "ok": ok_count > 0,
                "loss": round((attempts - ok_count) * 100 / max(1, attempts)),
                "latency_ms": round(avg, 1),
                "best_ms": round(best, 1),
                "jitter_ms": round(max(latencies) - min(latencies), 1) if len(latencies) > 1 else 0.0,
                "error": last_error if not ok_count else "",
            })

    started = time.time()
    await asyncio.gather(*(worker(t) for t in targets[:256]))
    live = [r for r in results if r["ok"]]
    live.sort(key=lambda r: (r["loss"], r["latency_ms"]))
    dead = sorted([r for r in results if not r["ok"]], key=lambda r: r["target"])
    return {
        "scanned": len(results),
        "alive": len(live),
        "seconds": round(time.time() - started, 2),
        "port": port,
        "tls": use_tls,
        "best": live[0] if live else None,
        "results": live + dead,
    }


async def scan_upstreams(entries: list[str], *, attempts: int = 2, timeout: float = 3.0) -> dict:
    """چک کردن پروکسی/تانل‌های بالادستی و برگرداندن سالم‌ها بر اساس تأخیر."""
    sem = asyncio.Semaphore(16)
    out: list[dict] = []

    async def worker(entry: str) -> None:
        from .egress import parse_proxy_entry
        from .vless_client import ChainError, open_stream

        conf = parse_proxy_entry(entry)
        async with sem:
            started = time.perf_counter()
            if conf and conf.get("host"):
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(conf["host"], int(conf["port"])), timeout=timeout
                    )
                    writer.close()
                    out.append({"entry": entry, "kind": "proxy", "ok": True,
                                "latency_ms": round((time.perf_counter() - started) * 1000, 1), "error": ""})
                    return
                except Exception as exc:
                    out.append({"entry": entry, "kind": "proxy", "ok": False, "latency_ms": 0,
                                "error": f"{type(exc).__name__}: {exc}"[:120]})
                    return
            out.append({"entry": entry, "kind": "chain", "ok": False, "latency_ms": 0,
                        "error": "قالب نامشخص (host:port بده)"})

    await asyncio.gather(*(worker(e) for e in entries[:64]))
    out.sort(key=lambda r: (not r["ok"], r["latency_ms"]))
    return {"checked": len(out), "alive": len([r for r in out if r["ok"]]),
            "best": out[0]["entry"] if out and out[0]["ok"] else None, "results": out}


async def scan_remote_list(url: str, timeout: float = 10.0) -> list[str]:
    """لیست پیشنهادی آی‌پی‌های تمیز را از یک منبع متنی/JSON می‌خواند (اختیاری)."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
    resp.raise_for_status()
    text = resp.text
    if text.lstrip().startswith(("[", "{")):
        with contextlib.suppress(Exception):
            import json

            data = json.loads(text)
            items = data if isinstance(data, list) else (data.get("ips") or data.get("list") or [])
            return [str(x).strip() for x in items if str(x).strip()][:256]
    out = []
    for line in text.splitlines():
        line = line.strip().split()[0] if line.strip() else ""
        if not line or line.startswith("#"):
            continue
        with contextlib.suppress(ValueError):
            ipaddress.ip_address(line.split(":")[0])
            out.append(line)
    return out[:256]
