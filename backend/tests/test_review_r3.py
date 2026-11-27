"""Regression tests for code-review round 3 (codex-r3-findings)."""
import pytest
from sqlalchemy import event

from tests.test_ingest import post, rd


# --- sparse ingest: work bounded by batch size, not by history ------------------------------
def _seed_history(client, key, n=300):
    from datetime import datetime, timedelta, timezone
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items = [rd((base + timedelta(minutes=i)).isoformat(), energy_kwh_total=float(i)) for i in range(n)]
    assert post(client, key, items).json()["inserted"] == n


def test_sparse_batch_does_not_range_scan_history(client, engine, meter_a):
    _, key = meter_a
    _seed_history(client, key)
    stmts = []

    def grab(conn, cursor, statement, params, context, executemany):
        stmts.append(statement)

    event.listen(engine, "before_cursor_execute", grab)
    try:
        r = post(client, key, [rd("2026-01-01T00:00:30+00:00", energy_kwh_total=0.5),
                               rd("2026-01-01T04:00:30+00:00", energy_kwh_total=240.5)])
    finally:
        event.remove(engine, "before_cursor_execute", grab)
    assert r.status_code == 200, r.text
    scans = [s for s in stmts if "FROM readings" in s and ">=" in s and "<=" in s and "LIMIT" not in s]
    assert not scans, scans


def test_sparse_batch_still_detects_register_violation(client, meter_a):
    _, key = meter_a
    _seed_history(client, key)
    # 1000 kWh at 00:00:30 is above the stored later value (1 at 00:01)
    r = post(client, key, [rd("2026-01-01T00:00:30+00:00", energy_kwh_total=1000),
                           rd("2026-01-01T04:00:30+00:00", energy_kwh_total=5000)])
    assert r.status_code == 422
    assert r.json()["detail"][0]["item"] == 0
    # and a value below the stored earlier reading after the end of history
    r = post(client, key, [rd("2026-01-01T06:00:00+00:00", energy_kwh_total=1)])
    assert r.status_code == 422


def test_duplicates_in_sparse_batch_still_counted(client, meter_a):
    _, key = meter_a
    _seed_history(client, key, 10)
    r = post(client, key, [rd("2026-01-01T00:03:00+00:00", energy_kwh_total=3),
                           rd("2026-01-01T09:00:00+00:00", energy_kwh_total=900)])
    assert r.json() == {"received": 2, "inserted": 1, "duplicates": 1}


# --- magnitude bounds ---------------------------------------------------------------------
@pytest.mark.parametrize("field", ["power_kw", "energy_kwh_total", "kvarh_total"])
def test_huge_magnitudes_rejected(client, meter_a, field):
    _, key = meter_a
    r = post(client, key, [rd("2026-07-01T00:00:00+08:00", **{field: 1e300})])
    assert r.status_code == 422, r.text


def test_huge_magnitude_rejected_in_csv(client, world, meter_a):
    from tests.test_csv import upload
    m, _ = meter_a
    r = upload(client, world.h_oa_a, m["id"], b"ts,power_kw\n2026-07-01T00:00:00+08:00,1e300\n")
    assert r.status_code == 422, r.text


def test_realistic_large_values_accepted(client, meter_a):
    _, key = meter_a
    r = post(client, key, [rd("2026-07-01T00:00:00+08:00", 500000.0, energy_kwh_total=9e9, kvarh_total=9e9)])
    assert r.status_code == 200, r.text


# --- unrepresentable dates ----------------------------------------------------------------
@pytest.mark.parametrize("d", ["0001-01-01", "9999-12-31"])
def test_unrepresentable_date_is_422(client, world, meter_a, d):
    m, _ = meter_a
    base = f"/api/v1/meters/{m['id']}"
    assert client.get(f"{base}/demand?date={d}", headers=world.h_oa_a).status_code == 422
    assert client.get(f"{base}/daily?start={d}&end={d}", headers=world.h_oa_a).status_code == 422
    assert client.get(f"/api/v1/sites/{world.site_a.id}/summary?date={d}", headers=world.h_oa_a).status_code == 422


# --- CORS preflight ----------------------------------------------------------------------
def test_cors_preflight_allows_api_key_header(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    monkeypatch.setenv("CORS_ORIGINS", "http://good.example")
    c = TestClient(create_app())
    r = c.options("/api/v1/ingest", headers={"Origin": "http://good.example",
                                              "Access-Control-Request-Method": "POST",
                                              "Access-Control-Request-Headers": "x-api-key,content-type"})
    assert r.status_code == 200, r.text
