"""Regression tests for code-review round 1 (codex-r1-findings)."""
import dataclasses
import inspect
import threading
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.services.billing import compute_bill
from tests.helpers import grid, utc
from tests.test_bill import meter, month_samples
from tests.test_energy_api import feed


# --- P1 meter-row lock ----------------------------------------------------------------

def test_store_readings_waits_for_meter_row_lock(engine, world, meter_a):
    """Concurrent writers for one meter are serialised by SELECT ... FOR UPDATE on the meter row."""
    if engine.dialect.name != "postgresql":
        pytest.skip("FOR UPDATE is a no-op on SQLite")
    from sqlalchemy.orm import Session

    from app import models
    from app.schemas import ReadingIn
    from app.services.ingest import store_readings

    m, _ = meter_a
    holder = Session(engine)
    # FOR NO KEY UPDATE conflicts with the writer's FOR UPDATE but not with the FK key-share
    # locks of plain INSERTs, so only an explicit meter lock makes the writer wait.
    holder.execute(select(models.Meter.id).where(models.Meter.id == m["id"])
                   .with_for_update(key_share=True))
    done = threading.Event()

    def writer():
        with Session(engine) as s:
            meter_row = s.get(models.Meter, m["id"])
            store_readings(s, meter_row, [ReadingIn(ts=datetime(2026, 7, 1, tzinfo=timezone.utc),
                                                    power_kw=1.0)], "api")
        done.set()

    t = threading.Thread(target=writer)
    t.start()
    try:
        time.sleep(0.8)
        waited = not done.is_set()
    finally:
        holder.rollback()     # always release, or the writer (and test teardown) would hang
        holder.close()
    t.join(10)
    assert waited, "writer did not wait for the meter lock"
    assert done.is_set()


def test_store_readings_locks_meter_row_in_statement(engine, world, meter_a, monkeypatch):
    """Dialect-independent: the lock query carries a FOR UPDATE clause (compiled for Postgres)."""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Session

    from app import models
    from app.schemas import ReadingIn
    from app.services import ingest

    m, _ = meter_a
    seen = []

    def wrap(name):
        orig = getattr(Session, name)

        def spy(self, stmt, *a, **kw):
            try:
                seen.append(str(stmt.compile(dialect=postgresql.dialect())))
            except Exception:
                pass
            return orig(self, stmt, *a, **kw)
        monkeypatch.setattr(Session, name, spy)

    wrap("execute")
    wrap("scalars")
    with Session(engine) as s:
        ingest.store_readings(s, s.get(models.Meter, m["id"]),
                              [ReadingIn(ts=datetime(2026, 7, 1, tzinfo=timezone.utc), power_kw=1.0)], "api")
    first_reading_query = next(i for i, q in enumerate(seen) if "FROM readings" in q)
    lock_query = next(i for i, q in enumerate(seen) if "FROM meters" in q and "FOR UPDATE" in q)
    assert lock_query < first_reading_query


# --- P1 PF needs kVARh coverage ------------------------------------------------------------

def _with_kvarh(samples, keep):
    return [dataclasses.replace(s, kvarh_total=(float(i) if keep(i, len(samples)) else None))
            for i, s in enumerate(samples)]


def test_pf_not_applied_when_kvarh_covers_no_interval():
    # kVARh only on first and last reading of the month: no interval has both ends -> not "measured 0"
    base = month_samples(2026, 7, with_registers=True)
    b = compute_bill(meter(), _with_kvarh(base, lambda i, n: i in (0, n - 1)), "2026-07")
    assert b["pf_adjustment"]["available"] is False
    assert b["pf_adjustment"]["amount"] == 0.0
    assert b["total"] == pytest.approx(b["base_after_coefficient"])
    assert any("kVARh" in w for w in b["warnings"])


def test_pf_not_applied_when_kvarh_covers_only_part_of_the_kwh_intervals():
    base = month_samples(2026, 7, with_registers=True)
    b = compute_bill(meter(), _with_kvarh(base, lambda i, n: i < n // 2), "2026-07")
    assert b["pf_adjustment"]["available"] is False and b["pf_adjustment"]["amount"] == 0.0


def test_pf_applied_when_kvarh_covers_every_kwh_interval():
    b = compute_bill(meter(), month_samples(2026, 7, with_registers=True, kvarh_ratio=0.0), "2026-07")
    assert b["pf_adjustment"]["available"] is True
    assert b["pf_adjustment"]["points"] == 100 and b["pf_adjustment"]["rate"] == pytest.approx(-0.015)


# --- P2 zero-usage needs complete coverage -------------------------------------------------

def test_zero_usage_discount_needs_complete_month_coverage():
    start = utc("2026-06-30T16:00")   # 2026-07-01 00:00 Taipei
    samples = grid(start, start + timedelta(minutes=15), 15, power_kw=0.0, with_registers=True)
    b = compute_bill(meter(), samples, "2026-07")
    assert 0 < b["coverage"] < 1
    assert b["basic_charge"] == pytest.approx(23701.00)      # not halved
    assert any("覆蓋" in w for w in b["warnings"])


# --- P1 (lead) over-contract is prorated across (version, season) segments ------------------

def test_over_contract_prorated_in_cross_season_month():
    # May 2026: 1-15 non-summer (15 d), 16-31 summer (16 d). 150 kW flat; reg 100, ns 20, sat 10, off 10.
    # non-summer: cum peak 120 / sat 130 / off 140 -> raw 30/20/10 -> net 30/0/0
    #   tier1 = min(30, 10% of 120 = 12) = 12 x2 ; tier2 = 18 x3 -> 78 * 166.90 (regular) = 13,018.20
    # summer (ns contract not counted): cum 100/110/120 -> raw 50/40/30 -> net 50/0/0
    #   tier1 = 10 x2 ; tier2 = 40 x3 -> 140 * 223.60 = 31,304.00
    # prorated = (13,018.20*15 + 31,304.00*16)/31 = 696,137/31 = 22,456.03 (old, unprorated: 44,322.20)
    m = meter(reg=100, ns=20, sat=10, off=10)
    b = compute_bill(m, month_samples(2026, 5, power_kw=150.0), "2026-05")
    assert b["over_contract"]["amount"] == pytest.approx(22456.03)
    assert "TODO: 台電跨季超約附加費計算方式未核實，暫以日數比例" in b["assumptions"]
    peak_rows = [r for r in b["over_contract"]["items"] if r["period"] == "peak"]
    assert sorted(r["segment_days"] for r in peak_rows) == [15, 16]


def test_over_contract_single_segment_month_unchanged():
    b = compute_bill(meter(), month_samples(2026, 7, power_kw=150.0), "2026-07")
    assert all(r["segment_days"] == 31 for r in b["over_contract"]["items"])
    assert "TODO: 台電跨季超約附加費計算方式未核實，暫以日數比例" not in b["assumptions"]


# --- P2 carbon: round the org total once --------------------------------------------------------

def test_sum_scope2_rounds_once_after_summing():
    from app.services.carbon import sum_scope2_tco2e
    # 3 x (1 kWh * 0.466 kg) = 0.001398 t -> 0.001 ; each alone rounds to 0.000
    assert sum_scope2_tco2e([(1, 0.466)] * 3) == 0.001
    # mixed factors use each meter's own factor
    assert sum_scope2_tco2e([(1000, 0.466), (1000, 0.471)]) == 0.937


def test_org_scope2_total_not_sum_of_rounded_rows(client, world):
    keys = []
    for i in range(3):
        r = client.post("/api/v1/meters", headers=world.h_oa_a, json={
            "site_id": world.site_a.id, "name": f"tiny-{i}", "voltage": "high", "scheme": "two_stage",
            "contract_regular_kw": 100, "customer_category": "industrial"})
        assert r.status_code == 201, r.text
        keys.append(r.json()["api_key"])
    for k in keys:   # 1 kW for 1 h = 1 kWh -> 0.000466 t per meter
        feed(client, k, datetime(2025, 5, 1, tzinfo=timezone.utc),
             datetime(2025, 5, 1, 1, tzinfo=timezone.utc), 15, power=1.0)
    o = client.get(f"/api/v1/orgs/{world.org_a.id}/scope2?year=2025", headers=world.h_oa_a).json()
    assert [r["scope2_tco2e"] for r in o["meters"]] == [0.0, 0.0, 0.0]
    assert o["scope2_tco2e"] == 0.001


# --- P2 CSV endpoint must not block the event loop -----------------------------------------------

def test_csv_import_route_is_sync_so_it_runs_in_threadpool():
    from app.routers.ingest import import_csv
    assert not inspect.iscoroutinefunction(import_csv)


# --- P2 DB credentials with special characters -----------------------------------------------------

def test_database_url_built_from_parts_escapes_credentials(monkeypatch):
    from app.config import get_settings
    for k in ("DATABASE_URL",):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_USER", "ems@u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:w/rd#?%")
    monkeypatch.setenv("POSTGRES_DB", "ems")
    u = make_url(get_settings().database_url)
    assert (u.host, u.port, u.username, u.password, u.database) == ("db", 5432, "ems@u", "p@ss:w/rd#?%", "ems")
    assert u.drivername == "postgresql+psycopg"


def test_explicit_database_url_wins(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    assert get_settings().database_url == "sqlite:///x.db"


# --- P3 csv.Error -> 422 -------------------------------------------------------------------------

def _upload(client, headers, meter_id, content):
    return client.post(f"/api/v1/meters/{meter_id}/readings/csv", headers=headers,
                       files={"file": ("r.csv", content, "text/csv")})


def test_csv_field_over_parser_limit_is_422_not_500(client, world, meter_a):
    m, _ = meter_a
    big = b"x" * 200_000
    body = b"ts,power_kw\n2026-07-01T00:00:00+08:00," + big + b"\n"
    r = _upload(client, world.h_oa_a, m["id"], body)
    assert r.status_code == 422, r.text


def test_csv_header_over_parser_limit_is_422_not_500(client, world, meter_a):
    m, _ = meter_a
    r = _upload(client, world.h_oa_a, m["id"], b"ts," + b"x" * 200_000 + b"\n")
    assert r.status_code == 422, r.text
