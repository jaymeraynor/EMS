"""Runtime settings, read from environment variables (no network, no secrets in code)."""
from __future__ import annotations

import os
from dataclasses import dataclass

MIN_SECRET_LEN = 32


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    ems_env: str
    jwt_expire_minutes: int
    cors_origins: tuple[str, ...]
    ingest_max_future_skew_s: int
    max_gap_minutes: float
    max_csv_bytes: int
    bcrypt_rounds: int

    @property
    def is_test(self) -> bool:
        return self.ems_env == "test"


def resolve_database_url(env=None) -> str | None:
    """DATABASE_URL if set, else a URL built from POSTGRES_* parts (credentials escaped)."""
    e = os.environ if env is None else env
    if e.get("DATABASE_URL"):
        return e["DATABASE_URL"]
    host = e.get("POSTGRES_HOST")
    if not host:
        return None
    from sqlalchemy.engine import URL
    return URL.create(
        "postgresql+psycopg", username=e.get("POSTGRES_USER") or None,
        password=e.get("POSTGRES_PASSWORD") or None, host=host,
        port=int(e.get("POSTGRES_PORT", "5432")), database=e.get("POSTGRES_DB") or None,
    ).render_as_string(hide_password=False)


def get_settings() -> Settings:
    """Read settings fresh from the environment (cheap; keeps tests/monkeypatching simple)."""
    e = os.environ
    return Settings(
        database_url=resolve_database_url(e) or "sqlite:///./ems.db",
        jwt_secret=e.get("JWT_SECRET", ""),
        ems_env=e.get("EMS_ENV", "production"),
        jwt_expire_minutes=int(e.get("JWT_EXPIRE_MINUTES", "60")),
        cors_origins=tuple(o.strip() for o in e.get("CORS_ORIGINS", "").split(",") if o.strip()),
        ingest_max_future_skew_s=int(e.get("INGEST_MAX_FUTURE_SKEW_S", "120")),
        max_gap_minutes=float(e.get("MAX_GAP_MINUTES", "15")),
        max_csv_bytes=int(e.get("MAX_CSV_BYTES", str(10 * 1024 * 1024))),
        bcrypt_rounds=int(e.get("BCRYPT_ROUNDS", "12")),
    )


PLACEHOLDER = "change-me"


def _db_password(env) -> str:
    from sqlalchemy.engine import make_url
    if env.get("DATABASE_URL"):
        try:
            return make_url(env["DATABASE_URL"]).password or ""
        except Exception:
            return ""
    return env.get("POSTGRES_PASSWORD", "")


def validate_for_startup(s: Settings) -> None:
    """Refuse to start with a missing/short/placeholder secret (except EMS_ENV=test)."""
    if s.is_test:
        return
    if len(s.jwt_secret) < MIN_SECRET_LEN:
        raise RuntimeError(
            f"JWT_SECRET must be set and at least {MIN_SECRET_LEN} characters long")
    if PLACEHOLDER in s.jwt_secret.lower():
        raise RuntimeError(f"JWT_SECRET still contains the '{PLACEHOLDER}' placeholder from .env.example")
    if PLACEHOLDER in _db_password(os.environ).lower():
        raise RuntimeError(f"The database password still contains the '{PLACEHOLDER}' placeholder from .env.example")
