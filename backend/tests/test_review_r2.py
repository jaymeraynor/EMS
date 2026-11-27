"""Regression tests for code-review round 2 (codex-r2-findings)."""
import pytest

from tests.test_csv import upload


def test_unterminated_quote_rejected(client, world, meter_a):
    m, _ = meter_a
    body = b'ts,power_kw\n2026-07-01T00:00:00+08:00,"123'
    r = upload(client, world.h_oa_a, m["id"], body)
    assert r.status_code == 422, r.text
    total = client.get(f"/api/v1/meters/{m['id']}/readings", headers=world.h_oa_a).json()["total"]
    assert total == 0


@pytest.mark.parametrize("month", ["0000-01", "0001-01", "9999-12"])
def test_unrepresentable_month_is_422(client, world, meter_a, month):
    m, _ = meter_a
    r = client.get(f"/api/v1/meters/{m['id']}/bill?month={month}", headers=world.h_oa_a)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("secret,pw", [
    ("change-me-to-a-long-random-string-of-32+chars", None),
    ("x" * 40 + "change-me", None),
    ("s" * 40, "change-me"),
])
def test_placeholder_secrets_refused_in_production(monkeypatch, secret, pw):
    from app.main import create_app
    monkeypatch.setenv("EMS_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", secret)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    if pw:
        monkeypatch.setenv("POSTGRES_HOST", "db")
        monkeypatch.setenv("POSTGRES_PASSWORD", pw)
    with pytest.raises(RuntimeError, match="change-me"):
        create_app()


def test_placeholder_db_password_in_database_url_refused(monkeypatch):
    from app.main import create_app
    monkeypatch.setenv("EMS_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "s" * 40)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://ems:change-me@db/ems")
    with pytest.raises(RuntimeError, match="change-me"):
        create_app()


def test_placeholder_allowed_in_test_env(monkeypatch):
    from app.config import get_settings, validate_for_startup
    monkeypatch.setenv("EMS_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "change-me" + "x" * 40)
    validate_for_startup(get_settings())
