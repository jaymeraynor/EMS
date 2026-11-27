import hashlib

import pytest

from app import models


def meter_payload(site_id, name="M1"):
    return {"site_id": site_id, "name": name, "voltage": "high", "scheme": "two_stage",
            "customer_category": "industrial"}


# --- roles -------------------------------------------------------------------------

def test_viewer_is_read_only(client, world):
    h = world.h_viewer_a
    assert client.get("/api/v1/sites", headers=h).status_code == 200
    assert client.post("/api/v1/sites", headers=h, json={"name": "x"}).status_code == 403
    assert client.post("/api/v1/meters", headers=h, json=meter_payload(world.site_a.id)).status_code == 403
    assert client.post("/api/v1/users", headers=h, json={
        "email": "n@x.test", "password": "a-long-password", "role": "viewer"}).status_code == 403
    assert client.post("/api/v1/orgs", headers=h, json={"name": "O"}).status_code == 403


def test_viewer_cannot_modify_or_rotate_or_import(client, world, meter_a):
    m, _ = meter_a
    h = world.h_viewer_a
    assert client.patch(f"/api/v1/meters/{m['id']}", headers=h, json={"name": "zz"}).status_code == 403
    assert client.post(f"/api/v1/meters/{m['id']}/rotate-key", headers=h).status_code == 403
    r = client.post(f"/api/v1/meters/{m['id']}/readings/csv", headers=h,
                    files={"file": ("a.csv", b"ts,power_kw\n", "text/csv")})
    assert r.status_code == 403
    assert client.get(f"/api/v1/meters/{m['id']}", headers=h).status_code == 200  # read ok


def test_org_admin_cannot_create_orgs_or_admins(client, world):
    h = world.h_oa_a
    assert client.post("/api/v1/orgs", headers=h, json={"name": "New"}).status_code == 403
    r = client.post("/api/v1/users", headers=h, json={
        "email": "evil-admin@x.test", "password": "a-long-password", "role": "admin"})
    assert r.status_code == 403


def test_org_admin_creates_users_in_own_org_only(client, world, db_session):
    h = world.h_oa_a
    r = client.post("/api/v1/users", headers=h, json={
        "email": "new-viewer@x.test", "password": "a-long-password", "role": "viewer"})
    assert r.status_code == 201, r.text
    assert r.json()["org_id"] == world.org_a.id
    assert "password" not in r.json() and "password_hash" not in r.json()
    r = client.post("/api/v1/users", headers=h, json={
        "email": "x2@x.test", "password": "a-long-password", "role": "viewer", "org_id": world.org_b.id})
    assert r.status_code == 404
    emails = {u["email"] for u in client.get("/api/v1/users", headers=h).json()}
    assert "oa-b@x.test" not in emails and "oa-a@x.test" in emails


def test_admin_creates_org_and_users(client, world):
    h = world.h_admin
    org = client.post("/api/v1/orgs", headers=h, json={"name": "Org C"})
    assert org.status_code == 201
    oid = org.json()["id"]
    u = client.post("/api/v1/users", headers=h, json={
        "email": "c-admin@x.test", "password": "a-long-password", "role": "org_admin", "org_id": oid})
    assert u.status_code == 201
    # org users need an org; only admins have none
    bad = client.post("/api/v1/users", headers=h, json={
        "email": "c2@x.test", "password": "a-long-password", "role": "viewer"})
    assert bad.status_code == 422
    assert len(client.get("/api/v1/orgs", headers=h).json()) >= 3


def test_duplicate_email_is_conflict(client, world):
    r = client.post("/api/v1/users", headers=world.h_admin, json={
        "email": "oa-a@x.test", "password": "a-long-password", "role": "viewer", "org_id": world.org_a.id})
    assert r.status_code == 409


def test_short_password_rejected(client, world):
    r = client.post("/api/v1/users", headers=world.h_admin, json={
        "email": "s@x.test", "password": "short", "role": "viewer", "org_id": world.org_a.id})
    assert r.status_code == 422


# --- org isolation -> 404 ------------------------------------------------------------------

def test_org_admin_sees_other_org_as_404(client, world):
    h_b = world.h_oa_b
    assert client.get(f"/api/v1/sites/{world.site_a.id}", headers=h_b).status_code == 404
    assert client.get(f"/api/v1/sites/{world.site_a.id}/summary?date=2026-07-01", headers=h_b).status_code == 404
    assert client.get(f"/api/v1/orgs/{world.org_a.id}/scope2?year=2025", headers=h_b).status_code == 404
    ids = [s["id"] for s in client.get("/api/v1/sites", headers=h_b).json()]
    assert ids == [world.site_b.id]
    # cannot create a meter inside someone else's site
    r = client.post("/api/v1/meters", headers=h_b, json=meter_payload(world.site_a.id))
    assert r.status_code == 404


def test_meter_of_other_org_is_404_everywhere(client, world, meter_a):
    m, _ = meter_a
    h = world.h_oa_b
    mid = m["id"]
    for method, path, kw in [
        ("get", f"/api/v1/meters/{mid}", {}),
        ("patch", f"/api/v1/meters/{mid}", {"json": {"name": "hax"}}),
        ("post", f"/api/v1/meters/{mid}/rotate-key", {}),
        ("get", f"/api/v1/meters/{mid}/readings", {}),
        ("get", f"/api/v1/meters/{mid}/daily?start=2026-07-01&end=2026-07-02", {}),
        ("get", f"/api/v1/meters/{mid}/demand?date=2026-07-01", {}),
        ("get", f"/api/v1/meters/{mid}/bill?month=2026-07", {}),
        ("get", f"/api/v1/meters/{mid}/scope2?year=2025", {}),
        ("post", f"/api/v1/meters/{mid}/readings/csv",
         {"files": {"file": ("a.csv", b"ts,power_kw\n", "text/csv")}}),
    ]:
        r = getattr(client, method)(path, headers=h, **kw)
        assert r.status_code == 404, (method, path, r.status_code)
    assert client.get("/api/v1/meters", headers=h).json() == []


def test_admin_sees_all_orgs(client, world, meter_a):
    m, _ = meter_a
    assert client.get(f"/api/v1/meters/{m['id']}", headers=world.h_admin).status_code == 200
    assert len(client.get("/api/v1/sites", headers=world.h_admin).json()) == 2


# --- API keys ---------------------------------------------------------------------------------

def test_api_key_returned_once_and_only_hash_stored(client, world, meter_a, db_session):
    m, key = meter_a
    assert key.startswith("ems_") and len(key) > 30
    assert "api_key" not in client.get(f"/api/v1/meters/{m['id']}", headers=world.h_oa_a).json()
    row = db_session.get(models.Meter, m["id"])
    assert row.api_key_hash == hashlib.sha256(key.encode()).hexdigest()
    assert row.api_key_prefix == key[:8]
    assert key not in str(row.__dict__)


def test_rotate_key_invalidates_old_key(client, world, meter_a):
    m, old = meter_a
    r = client.post(f"/api/v1/meters/{m['id']}/rotate-key", headers=world.h_oa_a)
    assert r.status_code == 200
    new = r.json()["api_key"]
    assert new != old
    body = {"readings": [{"ts": "2026-07-01T00:00:00+08:00", "power_kw": 1}]}
    assert client.post("/api/v1/ingest", headers={"X-API-Key": old}, json=body).status_code == 401
    assert client.post("/api/v1/ingest", headers={"X-API-Key": new}, json=body).status_code == 200


def test_api_key_writes_only_its_own_meter(client, world, meter_a):
    m1, key1 = meter_a
    r = client.post("/api/v1/meters", headers=world.h_oa_a, json=meter_payload(world.site_a.id, "M2"))
    m2 = r.json()
    body = {"readings": [{"ts": "2026-07-01T00:00:00+08:00", "power_kw": 5}]}
    assert client.post("/api/v1/ingest", headers={"X-API-Key": key1}, json=body).status_code == 200
    r1 = client.get(f"/api/v1/meters/{m1['id']}/readings", headers=world.h_oa_a).json()
    r2 = client.get(f"/api/v1/meters/{m2['id']}/readings", headers=world.h_oa_a).json()
    assert len(r1["items"]) == 1 and r2["items"] == []
    # a meter_id in the body is not accepted (the key decides)
    bad = {"meter_id": m2["id"], "readings": body["readings"]}
    assert client.post("/api/v1/ingest", headers={"X-API-Key": key1}, json=bad).status_code == 422


def test_api_key_is_not_a_login_credential(client, world, meter_a):
    _, key = meter_a
    assert client.get("/api/v1/meters", headers={"X-API-Key": key}).status_code == 401
    assert client.get("/api/v1/meters", headers={"Authorization": f"Bearer {key}"}).status_code == 401


def test_jwt_cannot_ingest(client, world, meter_a):
    body = {"readings": [{"ts": "2026-07-01T00:00:00+08:00", "power_kw": 5}]}
    assert client.post("/api/v1/ingest", headers=world.h_admin, json=body).status_code == 401


def test_update_meter_tariff_fields(client, world, meter_a):
    m, _ = meter_a
    r = client.patch(f"/api/v1/meters/{m['id']}", headers=world.h_oa_a, json={
        "contract_regular_kw": 250.5, "scheme": "three_stage", "industry_adjustment_coef": 0.896})
    assert r.status_code == 200
    assert r.json()["contract_regular_kw"] == 250.5 and r.json()["scheme"] == "three_stage"
    assert r.json()["industry_adjustment_coef"] == 0.896
    bad = client.patch(f"/api/v1/meters/{m['id']}", headers=world.h_oa_a, json={"voltage": "low"})
    assert bad.status_code == 422
    neg = client.patch(f"/api/v1/meters/{m['id']}", headers=world.h_oa_a, json={"contract_regular_kw": -1})
    assert neg.status_code == 422


def test_forecast_is_not_enabled(client, world):
    r = client.get("/api/v1/forecast", headers=world.h_viewer_a)
    assert r.status_code == 501
    assert r.json() == {"status": "未啟用", "detail": "預測模型尚未建置"}
