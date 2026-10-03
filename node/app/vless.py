"""پارس هدر پروتکل VLESS (نسخه‌ی ۰).

ساختار درخواست:
    1 بایت  نسخه
    16 بایت UUID
    1 بایت  طول addon
    n بایت  addon
    1 بایت  command (1=TCP, 2=UDP)
    2 بایت  پورت
    1 بایت  نوع آدرس (1=IPv4, 2=Domain, 3=IPv6)
    m بایت  آدرس
    ...     payload

پاسخ سرور: دو بایت (نسخه=۰، طول addon=۰) که فقط یک‌بار و پیش از اولین داده ارسال می‌شود.
"""

from __future__ import annotations

import uuid as uuid_lib
from dataclasses import dataclass

CMD_TCP = 1
CMD_UDP = 2

RESPONSE_HEADER = b"\x00\x00"


class NeedMoreData(Exception):
    """بایت کافی برای پارس هدر نرسیده است."""


class VlessError(Exception):
    """هدر نامعتبر / کاربر ناشناس."""


@dataclass
class VlessRequest:
    version: int
    uuid: str
    command: int
    address: str
    port: int
    payload: bytes
    addons: bytes = b""


def parse_request(buf: bytes) -> VlessRequest:
    if len(buf) < 18:
        raise NeedMoreData("header too short")
    version = buf[0]
    uid = str(uuid_lib.UUID(bytes=bytes(buf[1:17])))
    pos = 17
    addon_len = buf[pos]
    pos += 1
    if len(buf) < pos + addon_len + 4:
        raise NeedMoreData("addons incomplete")
    addons = bytes(buf[pos : pos + addon_len])
    pos += addon_len
    command = buf[pos]
    pos += 1
    port = int.from_bytes(buf[pos : pos + 2], "big")
    pos += 2
    addr_type = buf[pos]
    pos += 1
    if addr_type == 1:
        if len(buf) < pos + 4:
            raise NeedMoreData("ipv4 incomplete")
        address = ".".join(str(b) for b in buf[pos : pos + 4])
        pos += 4
    elif addr_type == 2:
        if len(buf) < pos + 1:
            raise NeedMoreData("domain length missing")
        dlen = buf[pos]
        pos += 1
        if len(buf) < pos + dlen:
            raise NeedMoreData("domain incomplete")
        address = bytes(buf[pos : pos + dlen]).decode("utf-8", "ignore")
        pos += dlen
    elif addr_type == 3:
        if len(buf) < pos + 16:
            raise NeedMoreData("ipv6 incomplete")
        raw = bytes(buf[pos : pos + 16])
        pos += 16
        address = ":".join(f"{raw[i]:02x}{raw[i + 1]:02x}" for i in range(0, 16, 2))
    else:
        raise VlessError(f"unknown address type {addr_type}")

    if not address or port <= 0:
        raise VlessError("bad destination")
    if command not in (CMD_TCP, CMD_UDP):
        raise VlessError(f"unsupported command {command}")

    return VlessRequest(
        version=version,
        uuid=uid,
        command=command,
        address=address,
        port=port,
        payload=bytes(buf[pos:]),
        addons=addons,
    )
