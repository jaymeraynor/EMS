"""Shared pytest setup.

Environment is configured *before* any ``app`` import so the settings pick it up.
DB-backed fixtures use TEST_DATABASE_URL (Postgres) when set, else a SQLite file.
"""
import os
import tempfile
import uuid

os.environ["EMS_ENV"] = "test"
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-0123")

import pytest  # noqa: E402

_SQLITE_DIR = tempfile.mkdtemp(prefix="ems-test-")


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    return f"sqlite:///{_SQLITE_DIR}/ems_{uuid.uuid4().hex}.db"


@pytest.fixture(scope="session")
def database_url() -> str:
    return _database_url()


@pytest.fixture(scope="session")
def engine(database_url):
    from app import db as dbmod
    from app.models import Base

    eng = dbmod.make_engine(database_url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    from sqlalchemy.orm import Session

    from app.models import Base

    with Session(engine) as session:
        yield session
    # wipe all rows between tests (children first)
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture()
def client(engine, db_session):
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.main import create_app

    app = create_app()

    def _override():
        from sqlalchemy.orm import Session

        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c


PASSWORD = "correct-horse-battery"


class World:
    """Two orgs with users of each role, one site each, plus ready-made auth headers."""


@pytest.fixture()
def world(db_session):
    from app import models, security

    s = db_session
    w = World()
    w.org_a = models.Organization(name="Org A")
    w.org_b = models.Organization(name="Org B")
    s.add_all([w.org_a, w.org_b])
    s.flush()

    def user(email, role, org):
        u = models.User(email=email, password_hash=security.hash_password(PASSWORD), role=role,
                        org_id=org.id if org else None, is_active=True)
        s.add(u)
        s.flush()
        return u

    w.admin = user("admin@x.test", "admin", None)
    w.oa_a = user("oa-a@x.test", "org_admin", w.org_a)
    w.viewer_a = user("v-a@x.test", "viewer", w.org_a)
    w.oa_b = user("oa-b@x.test", "org_admin", w.org_b)
    w.site_a = models.Site(org_id=w.org_a.id, name="Site A")
    w.site_b = models.Site(org_id=w.org_b.id, name="Site B")
    s.add_all([w.site_a, w.site_b])
    s.commit()

    def hdr(u):
        return {"Authorization": f"Bearer {security.create_access_token(u.id)}"}

    w.h_admin, w.h_oa_a, w.h_viewer_a, w.h_oa_b = (
        hdr(w.admin), hdr(w.oa_a), hdr(w.viewer_a), hdr(w.oa_b))
    return w


@pytest.fixture()
def meter_a(client, world):
    """A meter in org A created through the API; returns (meter_json, api_key)."""
    r = client.post("/api/v1/meters", headers=world.h_oa_a, json={
        "site_id": world.site_a.id, "name": "M-A1", "voltage": "high", "scheme": "two_stage",
        "contract_regular_kw": 100, "contract_sat_semi_peak_kw": 40, "contract_off_peak_kw": 40,
        "customer_category": "industrial"})
    assert r.status_code == 201, r.text
    body = r.json()
    return body, body["api_key"]
