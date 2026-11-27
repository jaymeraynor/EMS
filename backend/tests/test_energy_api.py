"""End-to-end calculations through the API."""
from datetime import datetime, timedelta, timezone

import pytest


def feed(client, key, start_utc, end_utc, step_min, power=60.0, extra=None):
    t, items = start_utc, []
    while t <= end_utc:
        items.append({"ts": t.isoformat(), "power_kw": power, **(extra(t) if extra else {})})
        t += timedelta(minutes=step_min)
    for i in range(0, len(items), 5000):
        r = client.post("/api/v1/ingest", headers={"X-API-Key": key}, json={"readings": items[i:i + 5000]})
        assert r.status_code == 200, r.text


U = lambda *a: datetime(*a, tzinfo=timezone.utc)  # noqa: E731


def test_daily_uses_taipei_days(client, world, meter_a):
    m, key = meter_a
    # 60 kW from 2026-07-01T15:00Z (23:00 Taipei 07-01) to 2026-07-02T16:00Z (24:00 07-02)
    feed(client, key, U(2026, 7, 1, 15), U(2026, 7, 2, 16), 15)
    r = client.get(f"/api/v1/meters/{m['id']}/daily?start=2026-07-01&end=2026-07-02", headers=world.h_oa_a)
    assert r.status_code == 200
    d1, d2 = r.json()
    assert d1["date"] == "2026-07-01" and d1["kwh"] == pytest.approx(60.0)
    assert d1["coverage"] == pytest.approx(1 / 24)
    assert d2["date"] == "2026-07-02" and d2["kwh"] == pytest.approx(60.0 * 24)
    assert d2["coverage"] == pytest.approx(1.0)


def test_daily_validates_range(client, world, meter_a):
    m, _ = meter_a
    h = world.h_oa_a
    assert client.get(f"/api/v1/meters/{m['id']}/daily?start=2026-07-02&end=2026-07-01", headers=h).status_code == 422
    assert client.get(f"/api/v1/meters/{m['id']}/daily?start=2026-01-01&end=2027-12-31", headers=h).status_code == 422
    assert client.get(f"/api/v1/meters/{m['id']}/daily?start=bad&end=2026-07-01", headers=h).status_code == 422


def test_demand_endpoint(client, world, meter_a):
    m, key = meter_a
    feed(client, key, U(2026, 7, 1, 16, 10), U(2026, 7, 1, 17, 0), 5, power=80.0)  # Taipei 00:10-01:00
    r = client.get(f"/api/v1/meters/{m['id']}/demand?date=2026-07-02", headers=world.h_oa_a)
    body = r.json()
    assert len(body["blocks"]) == 96
    assert body["blocks"][0]["complete"] is False
    assert body["blocks"][1]["demand_kw"] == pytest.approx(80.0) and body["blocks"][1]["complete"]
    assert body["max_demand_kw"] == pytest.approx(80.0)    # complete blocks only
    assert body["incomplete_blocks"] == 96 - 3             # blocks 1,2,3 complete; 0 and 4.. not
    assert body["blocks"][0]["start"].startswith("2026-07-02T00:00:00+08:00")


def test_site_summary_sums_simultaneous_blocks(client, world, meter_a):
    m1, key1 = meter_a
    r = client.post("/api/v1/meters", headers=world.h_oa_a, json={
        "site_id": world.site_a.id, "name": "M2", "voltage": "high", "scheme": "two_stage",
        "customer_category": "industrial"})
    key2 = r.json()["api_key"]
    # Taipei 07-02 00:00-01:00. M1 100 kW in first half hour then 0; M2 0 then 100 kW.
    # per-meter max = 100 each (sum 200) but simultaneous max = 100.
    items1 = [{"ts": (U(2026, 7, 1, 16) + timedelta(minutes=i)).isoformat(),
               "power_kw": 100.0 if i < 30 else 0.0} for i in range(0, 61)]
    items2 = [{"ts": (U(2026, 7, 1, 16) + timedelta(minutes=i)).isoformat(),
               "power_kw": 0.0 if i < 30 else 100.0} for i in range(0, 61)]
    for key, items in ((key1, items1), (key2, items2)):
        assert client.post("/api/v1/ingest", headers={"X-API-Key": key}, json={"readings": items}).status_code == 200
    r = client.get(f"/api/v1/sites/{world.site_a.id}/summary?date=2026-07-02", headers=world.h_oa_a)
    assert r.status_code == 200
    body = r.json()
    assert len(body["meters"]) == 2
    # blocks: 00:00-00:15 M1=100 M2=0 ; 00:15-00:30 same ; 00:30-00:45 M1=0 M2=100 -> sum stays 100
    assert body["max_simultaneous_demand_kw"] == pytest.approx(100.0, abs=1e-6)
    assert body["kwh"] == pytest.approx(100.0, abs=1e-6)  # 50 + 50 kWh


def test_bill_endpoint_flat_july(client, world, meter_a):
    m, key = meter_a
    feed(client, key, U(2026, 6, 30, 16), U(2026, 7, 31, 16), 15, power=100.0)
    r = client.get(f"/api/v1/meters/{m['id']}/bill?month=2026-07", headers=world.h_oa_a)
    assert r.status_code == 200, r.text
    b = r.json()
    # same hand-computed numbers as test_bill: reg 100 / sat 40 / off 40 two-stage high summer
    assert b["total"] == pytest.approx(365065.00)
    assert b["tariff_version"] == "taipower-2025-10-01"
    assert client.get(f"/api/v1/meters/{m['id']}/bill?month=2026-13", headers=world.h_oa_a).status_code == 422


def test_bill_for_unsupported_scheme_is_501(client, world, meter_a, db_session):
    from app import models
    m, _ = meter_a
    row = db_session.get(models.Meter, m["id"])
    row.scheme = "batch_production"
    db_session.commit()
    r = client.get(f"/api/v1/meters/{m['id']}/bill?month=2026-07", headers=world.h_oa_a)
    assert r.status_code == 501


def test_scope2_meter_and_org(client, world, meter_a):
    m, key = meter_a
    # 1000 kW for 1 h in 2025 Taipei -> 1000 kWh ; industrial 0.466 -> 0.466 tCO2e
    feed(client, key, U(2025, 5, 1, 0), U(2025, 5, 1, 1), 15, power=1000.0)
    h = world.h_oa_a
    r = client.get(f"/api/v1/meters/{m['id']}/scope2?year=2025", headers=h)
    assert r.status_code == 200
    b = r.json()
    assert b["kwh"] == pytest.approx(1000.0)
    assert b["factor_kg_per_kwh"] == 0.466 and b["provisional"] is False
    assert b["scope2_tco2e"] == 0.466
    o = client.get(f"/api/v1/orgs/{world.org_a.id}/scope2?year=2025", headers=h).json()
    assert o["scope2_tco2e"] == 0.466 and len(o["meters"]) == 1
    # later year -> provisional ; earlier -> 422
    p = client.get(f"/api/v1/meters/{m['id']}/scope2?year=2026", headers=h).json()
    assert p["provisional"] is True and p["warnings"]
    assert client.get(f"/api/v1/meters/{m['id']}/scope2?year=2024", headers=h).status_code == 422


def test_scope2_uses_residential_factor(client, world, meter_a):
    m, key = meter_a
    client.patch(f"/api/v1/meters/{m['id']}", headers=world.h_oa_a, json={"customer_category": "residential"})
    feed(client, key, U(2025, 5, 1, 0), U(2025, 5, 1, 1), 15, power=1000.0)
    b = client.get(f"/api/v1/meters/{m['id']}/scope2?year=2025", headers=world.h_oa_a).json()
    assert b["scope2_tco2e"] == 0.471
