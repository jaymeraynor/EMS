GOOD = (b"ts,power_kw,energy_kwh_total,kvarh_total\n"
        b"2026-07-01T00:00:00+08:00,10,100,5\n"
        b"2026-07-01T00:15:00+08:00,12,103,6\n")


def upload(client, headers, meter_id, content, name="r.csv"):
    return client.post(f"/api/v1/meters/{meter_id}/readings/csv", headers=headers,
                       files={"file": (name, content, "text/csv")})


def count(client, world, meter_id):
    return client.get(f"/api/v1/meters/{meter_id}/readings", headers=world.h_oa_a).json()["total"]


def test_good_csv(client, world, meter_a, db_session):
    from app import models
    m, _ = meter_a
    r = upload(client, world.h_oa_a, m["id"], GOOD)
    assert r.status_code == 200, r.text
    assert r.json() == {"received": 2, "inserted": 2, "duplicates": 0}
    assert count(client, world, m["id"]) == 2
    b = db_session.query(models.IngestBatch).one()
    assert b.source == "csv" and b.user_id == world.oa_a.id and b.inserted == 2
    # re-upload: all duplicates
    r = upload(client, world.h_oa_a, m["id"], GOOD)
    assert r.json() == {"received": 2, "inserted": 0, "duplicates": 2}


def test_power_only_header_allowed(client, world, meter_a):
    m, _ = meter_a
    r = upload(client, world.h_admin, m["id"], b"ts,power_kw\n2026-07-01T00:00:00+08:00,3\n")
    assert r.status_code == 200 and r.json()["inserted"] == 1


def test_bad_rows_import_nothing_and_list_row_numbers(client, world, meter_a):
    m, _ = meter_a
    bad = (b"ts,power_kw\n"
           b"2026-07-01T00:00:00+08:00,10\n"       # row 2 ok
           b"2026-07-01T00:01:00,10\n"             # row 3 naive ts
           b"2026-07-01T00:02:00+08:00,-4\n"       # row 4 negative
           b"2026-07-01T00:03:00+08:00,abc\n")     # row 5 not a number
    r = upload(client, world.h_oa_a, m["id"], bad)
    assert r.status_code == 422
    errs = r.json()["detail"]
    assert [e["row"] for e in errs] == [3, 4, 5]
    assert all(e["error"] for e in errs)
    assert count(client, world, m["id"]) == 0


def test_error_list_capped_at_100(client, world, meter_a):
    m, _ = meter_a
    rows = b"".join(b"2026-07-01T00:00:00,1\n" for _ in range(150))
    r = upload(client, world.h_oa_a, m["id"], b"ts,power_kw\n" + rows)
    assert r.status_code == 422 and len(r.json()["detail"]) == 100


def test_register_decrease_reported_with_row(client, world, meter_a):
    m, _ = meter_a
    csv = (b"ts,power_kw,energy_kwh_total\n2026-07-01T00:00:00+08:00,1,10\n"
           b"2026-07-01T00:05:00+08:00,1,9\n")
    r = upload(client, world.h_oa_a, m["id"], csv)
    assert r.status_code == 422 and r.json()["detail"][0]["row"] == 3


def test_wrong_header_rejected(client, world, meter_a):
    m, _ = meter_a
    r = upload(client, world.h_oa_a, m["id"], b"time,kw\n2026-07-01T00:00:00+08:00,1\n")
    assert r.status_code == 422


def test_empty_file_rejected(client, world, meter_a):
    m, _ = meter_a
    assert upload(client, world.h_oa_a, m["id"], b"").status_code == 422
    assert upload(client, world.h_oa_a, m["id"], b"ts,power_kw\n").status_code == 422


def test_utf8_bom_header_is_accepted(client, world, meter_a):
    m, _ = meter_a
    r = upload(client, world.h_oa_a, m["id"], b"\xef\xbb\xbfts,power_kw\n2026-07-01T00:00:00+08:00,1\n")
    assert r.status_code == 200


def test_file_over_10mb_rejected(client, world, meter_a):
    m, _ = meter_a
    big = b"ts,power_kw\n" + b"#" * (10 * 1024 * 1024 + 1)
    assert upload(client, world.h_oa_a, m["id"], big).status_code == 413
    assert count(client, world, m["id"]) == 0
