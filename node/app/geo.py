"""تشخیص IP عمومی و موقعیت جغرافیایی نود (از مسیر خروج واقعی).

کاربرد: پنل بتواند IP و کشور هر لوکیشن را نشان دهد و بگوید خروجی واقعی کجاست
(اگر مسیر خروج proxy/chain باشد، IPِ همان مسیر دیده می‌شود، نه IP خود سرور).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import ssl
import time
from pathlib import Path

from . import settings
from .egress import egress

logger = logging.getLogger("mlp.node")

CACHE_FILE = Path(settings.DATA_DIR) / "geo.json"
PROVIDERS = [
    ("http://ip-api.com/json/?fields=status,message,country,countryCode,city,isp,as,query", False),
    ("https://ipinfo.io/json", True),
    ("https://ipwho.is/", True),
    ("https://api.myip.com", True),
    ("https://api.ipify.org?format=json", True),
]

# نگاشت کد کشور → فلگ (اگر کد ناشناس بود، 🌍)
FLAG_FALLBACK = "🌍"


def flag_for(country_code: str) -> str:
    code = (country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return FLAG_FALLBACK
    return chr(0x1F1E6 + ord(code[0]) - 65) + chr(0x1F1E6 + ord(code[1]) - 65)


COUNTRY_FA = {
    "DE": "آلمان", "NL": "هلند", "FR": "فرانسه", "GB": "انگلستان", "US": "آمریکا",
    "CA": "کانادا", "TR": "ترکیه", "IR": "ایران", "AE": "امارات", "RU": "روسیه",
    "SE": "سوئد", "FI": "فینلاند", "PL": "لهستان", "AT": "اتریش", "CH": "سوئیس",
    "IT": "ایتالیا", "ES": "اسپانیا", "IN": "هند", "SG": "سنگاپور", "JP": "ژاپن",
    "KR": "کره جنوبی", "AU": "استرالیا", "BR": "برزیل", "IE": "ایرلند", "BE": "بلژیک",
    "DK": "دانمارک", "NO": "نروژ", "CZ": "چک", "RO": "رومانی", "UA": "اوکراین",
    "HK": "هنگ‌کنگ", "CN": "چین", "IL": "اسرائیل", "SA": "عربستان", "QA": "قطر",
    "KW": "کویت", "OM": "عمان", "BH": "بحرین", "AM": "ارمنستان", "GE": "گرجستان",
    "AZ": "آذربایجان", "KZ": "قزاقستان", "PK": "پاکستان", "IQ": "عراق", "SY": "سوریه",
    "LB": "لبنان", "JO": "اردن", "EG": "مصر", "ZA": "آفریقای جنوبی", "MX": "مکزیک",
    "AR": "آرژانتین", "CL": "شیلی", "NZ": "نیوزیلند", "MY": "مالزی", "TH": "تایلند",
    "VN": "ویتنام", "ID": "اندونزی", "TW": "تایوان", "PH": "فیلیپین", "GR": "یونان",
    "PT": "پرتغال", "HU": "مجارستان", "BG": "بلغارستان", "RS": "صربستان", "LT": "لیتوانی",
    "LV": "لتونی", "EE": "استونی", "SK": "اسلواکی", "SI": "اسلوونی", "HR": "کرواسی",
    "MD": "مولداوی", "BY": "بلاروس", "CY": "قبرس", "MT": "مالت", "IS": "ایسلند",
    "LU": "لوکزامبورگ", "AL": "آلبانی", "MK": "مقدونیه", "BA": "بوسنی", "ME": "مونته‌نگرو",
}

# نگاشت ریجن Railway → (کد کشور، فلگ) برای حدس اولیه
RAILWAY_REGIONS = {
    "europe-west4": ("NL", "🇳🇱", "Amsterdam"),
    "europe-west3": ("DE", "🇩🇪", "Frankfurt"),
    "europe-west2": ("GB", "🇬🇧", "London"),
    "europe-west1": ("BE", "🇧🇪", "Brussels"),
    "us-east4": ("US", "🇺🇸", "Virginia"),
    "us-west2": ("US", "🇺🇸", "Los Angeles"),
    "us-east1": ("US", "🇺🇸", "South Carolina"),
    "asia-southeast1": ("SG", "🇸🇬", "Singapore"),
    "asia-south1": ("IN", "🇮🇳", "Mumbai"),
    "southamerica-east1": ("BR", "🇧🇷", "São Paulo"),
    "australia-southeast1": ("AU", "🇦🇺", "Sydney"),
    "us-central1": ("US", "🇺🇸", "Iowa"),
    "asia-northeast3": ("KR", "🇰🇷", "Seoul"),
}

_cache: dict = {}
_last_check = 0.0


def railway_region_hint(region: str) -> dict:
    code, flag, city = RAILWAY_REGIONS.get((region or "").strip(), ("", FLAG_FALLBACK, ""))
    return {"country_code": code, "flag": flag, "city": city, "country": COUNTRY_FA.get(code, code)}


def _parse(payload: dict, fallback_ip: str = "") -> dict:
    """تبدیل پاسخ سرویس‌های مختلف به یک قالب یکسان."""
    data = payload or {}
    ip = str(data.get("ip") or data.get("query") or data.get("IPv4") or fallback_ip or "").strip()
    code = str(
        data.get("countryCode") or data.get("country_code") or data.get("country_code2") or ""
    ).strip().upper()
    country = str(data.get("country") or data.get("country_name") or "").strip()
    city = str(data.get("city") or data.get("region") or "").strip()
    isp = str(data.get("isp") or data.get("org") or data.get("connection", {}).get("isp") or "").strip() \
        if isinstance(data.get("connection"), dict) else str(data.get("isp") or data.get("org") or "").strip()
    asn = str(data.get("as") or data.get("asn") or "").strip()
    if not code and country:
        for key, fa in COUNTRY_FA.items():
            if country.lower() == fa or country.lower() in fa.lower():
                code = key
                break
    return {
        "ip": ip,
        "country_code": code,
        "country": COUNTRY_FA.get(code, country or ""),
        "country_en": country,
        "flag": flag_for(code),
        "city": city,
        "isp": isp,
        "asn": asn,
        "checked_at": int(time.time()),
    }


async def _http_get(host: str, port: int, path: str, use_tls: bool, timeout: float = 8.0,
                    extra_headers: dict | None = None) -> str:
    """یک GET ساده HTTP/1.1 از مسیر خروج فعال (بدون وابستگی سنگین)."""
    reader, writer = await egress.connect(host, port, timeout=timeout)
    try:
        if use_tls:
            if not hasattr(writer, "start_tls"):
                raise RuntimeError("TLS روی این مسیر خروج پشتیبانی نمی‌شود")
            ctx = ssl.create_default_context()
            await asyncio.wait_for(
                writer.start_tls(ctx, server_hostname=host), timeout=timeout
            )
        headers = {
            "Host": host,
            "User-Agent": "Mozilla/5.0 (compatible; MLP-Node/1.1)",
            "Accept": "application/json",
            "Connection": "close",
        }
        headers.update(extra_headers or {})
        request = f"GET {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"
        writer.write(request.encode())
        await writer.drain()
        body = b""
        while len(body) < 65536:
            chunk = await asyncio.wait_for(reader.read(16384), timeout=timeout)
            if not chunk:
                break
            body += chunk
        head, _, payload = body.partition(b"\r\n\r\n")
        if b" 200" not in head.split(b"\r\n")[0]:
            raise RuntimeError(head.split(b"\r\n")[0].decode("latin-1", "replace")[:80])
        return payload.decode("utf-8", "replace")
    finally:
        with contextlib.suppress(Exception):
            writer.close()


def _provider_from_url(url: str) -> tuple[str, int, str, bool]:
    raw = url.split("://", 1)
    scheme = raw[0]
    rest = raw[1] if len(raw) > 1 else raw[0]
    hostport, _, path = rest.partition("/")
    path = "/" + path if path else "/"
    host, _, port = hostport.partition(":")
    use_tls = scheme == "https"
    return host, int(port or (443 if use_tls else 80)), path, use_tls


async def detect(force: bool = False, timeout: float = 8.0) -> dict:
    """IP و موقعیت خروجی فعلی را برمی‌گرداند (با کش)."""
    global _cache, _last_check
    if not settings.GEO_ENABLED:
        return {}
    if not force and _cache and (time.time() - _last_check) < settings.GEO_INTERVAL:
        return _cache

    providers = list(PROVIDERS)
    if settings.GEO_URL:
        providers.insert(0, (settings.GEO_URL, settings.GEO_URL.startswith("https")))
    chain_active = any(p.kind == "chain" for p in egress.paths if egress.mode in ("chain", "auto"))
    last_error = ""
    for url, want_tls in providers:
        host, port, path, use_tls = _provider_from_url(url)
        if chain_active:
            # روی تانل فقط HTTP ساده ممکن است (TLS روی کانال WS نداریم)
            if use_tls:
                continue
        try:
            text = await _http_get(host, port, path, use_tls, timeout=timeout)
            payload = json.loads(text)
            info = _parse(payload)
            if not info.get("ip"):
                continue
            info["via"] = egress.active or egress.mode
            info["mode"] = egress.mode
            _cache = info
            _last_check = time.time()
            with contextlib.suppress(Exception):
                CACHE_FILE.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
            logger.info("geo: %s %s (%s) via %s", info["ip"], info.get("country"), info["flag"], info["via"])
            return info
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue

    # اگر اینترنت نبود، آخرین مقدار ذخیره‌شده ارزش دارد
    if _cache:
        return _cache
    with contextlib.suppress(Exception):
        if CACHE_FILE.exists():
            _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            return _cache
    if last_error:
        logger.warning("geo lookup failed: %s", last_error)
    return {"error": last_error[:200], "flag": FLAG_FALLBACK}


def cached() -> dict:
    return dict(_cache)


async def geo_loop() -> None:
    if not settings.GEO_ENABLED:
        return
    await asyncio.sleep(8)
    while True:
        try:
            await detect(force=True)
        except Exception as exc:  # pragma: no cover
            logger.warning("geo loop error: %s", exc)
        await asyncio.sleep(max(120.0, settings.GEO_INTERVAL))
