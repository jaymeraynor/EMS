from datetime import datetime, timedelta, timezone

import pytest


def post(client, key, readings):
    return client.post("/api/v1/ingest", headers={"X-API-Key": key}, json={"readings": readings})


def rd(ts, p=10.0, **kw):
    return {"ts": ts, "power_kw": p, **kw}


def stored(client, world, meter_id):
    r = client.get(f"/api/v1/meters/{meter_id}/readings?limit=10000", headers=world.h_oa_a)
    return r.json()["items"]


def test_ingest_inserts_and_reports_counts(client, world, meter_a):
    m, key = meter_a
    r = post(client, key, [rd("2026-07-01T00:00:00+08:00", 10), rd("2026-07-01T00:00:05+08:00", 11)])
    assert r.status_code == 200
    assert r.json() == {"received": 2, "inserted": 2, "duplicates": 0}
    items = stored(client, world, m["id"])
    assert [i["power_kw"] for i in items] == [10, 11]
    # stored as UTC instants: 00:00+08:00 == 16:00Z previous day
    assert items[0]["ts"].startswith("2026-06-30T16:00:00")


def test_duplicates_existing_and_in_batch_are_counted_not_errors(client, world, meter_a):
    m, key = meter_a
    post(client, key, [rd("2026-07-01T00:00:00+08:00", 10)])
    r = post(client, key, [rd("2026-07-01T00:00:00+08:00", 99),       # existing
                           rd("2026-06-30T16:00:00Z", 98),            # same instant, other offset
                           rd("2026-07-01T00:01:00+08:00", 11),
                           rd("2026-07-01T00:01:00+08:00", 12)])      # in-batch dup
    assert r.status_code == 200
    assert r.json() == {"received": 4, "inserted": 1, "duplicates": 3}
    assert [i["power_kw"] for i in stored(client, world, m["id"])] == [10, 11]  # first wins


@pytest.mark.parametrize("bad", [
    {"ts": "2026-07-01T00:00:00+08:00", "power_kw": -1},
    {"ts": "2026-07-01T00:00:00+08:00", "power_kw": 1, "energy_kwh_total": -5},
    {"ts": "2026-07-01T00:00:00+08:00", "power_kw": 1, "kvarh_total": -5},
    {"ts": "2026-07-01T00:00:00", "power_kw": 1},                 # naive datetime
    {"ts": "2026-07-01", "power_kw": 1},
    {"ts": "not-a-date", "power_kw": 1},
    {"ts": "2026-07-01T00:00:00+08:00", "power_kw": "abc"},
    {"ts": "2026-07-01T00:00:00+08:00"},
])
def test_invalid_items_rejected_with_422(client, meter_a, bad):
    _, key = meter_a
    assert post(client, key, [bad]).status_code == 422


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_rejected(client, meter_a, literal):
    _, key = meter_a
    raw = '{"readings":[{"ts":"2026-07-01T00:00:00+08:00","power_kw":%s}]}' % literal
    r = client.post("/api/v1/ingest", headers={"X-API-Key": key, "Content-Type": "application/json"},
                    content=raw)
    assert r.status_code == 422


def test_future_timestamp_rejected_beyond_skew(client, meter_a):
    _, key = meter_a
    now = datetime.now(timezone.utc)
    ok = (now + timedelta(seconds=60)).isoformat()
    too_far = (now + timedelta(seconds=600)).isoformat()
    assert post(client, key, [rd(ok)]).status_code == 200
    assert post(client, key, [rd(too_far)]).status_code == 422


def test_batch_limit_5000(client, meter_a):
    _, key = meter_a
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items = [rd((base + timedelta(seconds=i)).isoformat()) for i in range(5001)]
    assert post(client, key, items).status_code == 422
    r = post(client, key, items[:5000])
    assert r.status_code == 200 and r.json()["inserted"] == 5000


def test_empty_batch_rejected(client, meter_a):
    _, key = meter_a
    assert post(client, key, []).status_code == 422


def test_register_decrease_vs_stored_reading_names_the_item(client, meter_a):
    _, key = meter_a
    assert post(client, key, [rd("2026-07-01T00:00:00+08:00", energy_kwh_total=100)]).status_code == 200
    r = post(client, key, [rd("2026-07-01T00:05:00+08:00", energy_kwh_total=101),
                           rd("2026-07-01T00:10:00+08:00", energy_kwh_total=50)])
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail[0]["item"] == 1 and "energy_kwh_total" in detail[0]["error"]


def test_register_decrease_inside_batch_even_if_unordered(client, meter_a):
    _, key = meter_a
    r = post(client, key, [rd("2026-07-01T00:10:00+08:00", energy_kwh_total=5),
                           rd("2026-07-01T00:00:00+08:00", energy_kwh_total=10)])
    assert r.status_code == 422
    assert r.json()["detail"][0]["item"] == 0   # the 00:10 item (5 < 10 earlier in time)


def test_kvarh_register_decrease_rejected(client, meter_a):
    _, key = meter_a
    r = post(client, key, [rd("2026-07-01T00:00:00+08:00", kvarh_total=10),
                           rd("2026-07-01T00:05:00+08:00", kvarh_total=9)])
    assert r.status_code == 422 and "kvarh_total" in r.json()["detail"][0]["error"]


def test_late_backfill_between_stored_readings_checked_against_both_neighbours(client, meter_a):
    _, key = meter_a
    post(client, key, [rd("2026-07-01T00:00:00+08:00", energy_kwh_total=10),
                       rd("2026-07-01T00:10:00+08:00", energy_kwh_total=20)])
    assert post(client, key, [rd("2026-07-01T00:05:00+08:00", energy_kwh_total=15)]).status_code == 200
    assert post(client, key, [rd("2026-07-01T00:06:00+08:00", energy_kwh_total=25)]).status_code == 422


def test_rejected_batch_inserts_nothing(client, world, meter_a):
    m, key = meter_a
    post(client, key, [rd("2026-07-01T00:00:00+08:00", 1), rd("2026-07-01T00:01:00+08:00", -1)])
    assert stored(client, world, m["id"]) == []


def test_invalid_or_missing_key_is_401(client):
    body = {"readings": [rd("2026-07-01T00:00:00+08:00")]}
    assert client.post("/api/v1/ingest", json=body).status_code == 401
    assert client.post("/api/v1/ingest", headers={"X-API-Key": "ems_nope"}, json=body).status_code == 401


def test_readings_list_range_and_paging_limits(client, world, meter_a):
    m, key = meter_a
    post(client, key, [rd(f"2026-07-01T00:0{i}:00+08:00", i) for i in range(5)])
    h = world.h_oa_a
    r = client.get(f"/api/v1/meters/{m['id']}/readings", headers=h,
                   params={"start": "2026-06-30T16:01:00Z", "end": "2026-06-30T16:04:00Z"})
    assert [i["power_kw"] for i in r.json()["items"]] == [1, 2, 3]
    page = client.get(f"/api/v1/meters/{m['id']}/readings?limit=2&offset=2", headers=h).json()
    assert [i["power_kw"] for i in page["items"]] == [2, 3] and page["total"] == 5
    assert client.get(f"/api/v1/meters/{m['id']}/readings?limit=10001", headers=h).status_code == 422
    assert client.get(f"/api/v1/meters/{m['id']}/readings?start=2026-07-01T00:00:00", headers=h).status_code == 422


def test_ingest_batch_audit_row_written(client, meter_a, db_session):
    from app import models
    _, key = meter_a
    post(client, key, [rd("2026-07-01T00:00:00+08:00"), rd("2026-07-01T00:00:00+08:00")])
    b = db_session.query(models.IngestBatch).one()
    assert (b.source, b.received, b.inserted, b.duplicates) == ("api", 2, 1, 1)
    assert b.user_id is None
