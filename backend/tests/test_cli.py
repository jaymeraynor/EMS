from sqlalchemy.orm import Session

from app import models


def test_create_admin_creates_login_capable_admin(engine, db_session, client):
    from app.cli import create_admin
    with Session(engine) as s:
        create_admin(s, "boss@x.test", "a-very-long-password")
    r = client.post("/api/v1/auth/login", data={"username": "boss@x.test", "password": "a-very-long-password"})
    assert r.status_code == 200
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["role"] == "admin" and me["org_id"] is None


def test_create_admin_rejects_duplicate_and_short_password(engine, db_session):
    import pytest
    from app.cli import create_admin
    with Session(engine) as s:
        create_admin(s, "a@x.test", "a-very-long-password")
    with Session(engine) as s:
        with pytest.raises(ValueError):
            create_admin(s, "a@x.test", "a-very-long-password")
        with pytest.raises(ValueError):
            create_admin(s, "b@x.test", "short")


def test_seed_demo_marks_meter_as_demo(engine, db_session):
    from app.cli import seed_demo
    with Session(engine) as s:
        seed_demo(s, days=2)
    with Session(engine) as s:
        meters = s.query(models.Meter).all()
        assert meters and all(m.is_demo for m in meters)
        assert s.query(models.Reading).count() > 0
        assert all(r.source == "csv" or r.source == "api" for r in s.query(models.Reading).limit(5))
