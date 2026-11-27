"""Password hashing (bcrypt), JWT (HS256) and meter API keys."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import get_settings

API_KEY_PREFIX = "ems_"
MAX_PASSWORD_BYTES = 72  # bcrypt limit


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(get_settings().bcrypt_rounds)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta if expires_delta is not None else timedelta(minutes=s.jwt_expire_minutes))
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": exp}, s.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> Optional[int]:
    """Return the user id, or None for any invalid/expired token."""
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"],
                          options={"require": ["exp", "sub"]})
        return int(data["sub"])
    except (jwt.PyJWTError, ValueError):
        return None


def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
