"""امنیت: هش رمز، نشست‌ها، توکن‌ها."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, _digest = stored.split("$", 2)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def new_token(prefix: str = "", nbytes: int = 24) -> str:
    return f"{prefix}{secrets.token_urlsafe(nbytes)}"


def new_uuid() -> str:
    import uuid as _uuid

    return str(_uuid.uuid4())


def now_ts() -> int:
    return int(time.time())


def random_path(prefix: str = "p") -> str:
    return f"/{prefix}-{secrets.token_hex(5)}"


def const_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
