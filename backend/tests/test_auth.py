from datetime import timedelta

import pytest

from app import security
from tests.conftest import PASSWORD


def login(client, email, password):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_login_and_me(client, world):
    r = login(client, "oa-a@x.test", PASSWORD)
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "oa-a@x.test"
    assert me.json()["role"] == "org_admin"
    assert me.json()["org_id"] == world.org_a.id
    assert "password_hash" not in me.json()


def test_wrong_password_and_unknown_user_look_the_same(client, world):
    a = login(client, "oa-a@x.test", "wrong-password")
    b = login(client, "nobody@x.test", PASSWORD)
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_inactive_user_cannot_login(client, world, db_session):
    world.viewer_a.is_active = False
    db_session.commit()
    assert login(client, "v-a@x.test", PASSWORD).status_code == 401


def test_expired_token_rejected(client, world):
    tok = security.create_access_token(world.admin.id, expires_delta=timedelta(seconds=-5))
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_token_signed_with_other_secret_rejected(client, world):
    import jwt
    tok = jwt.encode({"sub": str(world.admin.id), "exp": 9999999999}, "x" * 40, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_deactivated_user_token_stops_working(client, world, db_session):
    h = world.h_viewer_a
    world.viewer_a.is_active = False
    db_session.commit()
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_missing_token_is_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/sites").status_code == 401


def test_no_public_signup(client):
    for path in ("/api/v1/auth/register", "/api/v1/auth/signup"):
        assert client.post(path, json={"email": "a@b.c", "password": "x" * 12}).status_code in (404, 405)


def test_password_hash_is_bcrypt():
    h = security.hash_password("a-long-enough-password")
    assert h.startswith("$2") and security.verify_password("a-long-enough-password", h)
    assert not security.verify_password("other", h)


def test_app_refuses_to_start_without_strong_secret(monkeypatch):
    from app.main import create_app
    monkeypatch.setenv("EMS_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_app()
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_app()
    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    create_app()  # ok


def test_cors_default_allows_no_origin(client):
    r = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_origins_from_env(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    monkeypatch.setenv("CORS_ORIGINS", "http://good.example")
    c = TestClient(create_app())
    r = c.get("/api/v1/health", headers={"Origin": "http://good.example"})
    assert r.headers.get("access-control-allow-origin") == "http://good.example"
    r = c.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers
