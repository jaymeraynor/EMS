"""Migration must create exactly the schema the models describe and be reversible."""
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parent.parent


def _alembic(url, *args):
    env = {**os.environ, "DATABASE_URL": url}
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env,
                          capture_output=True, text=True)


@pytest.fixture()
def fresh_url(tmp_path):
    base = os.environ.get("TEST_DATABASE_URL")
    if not base:
        yield f"sqlite:///{tmp_path}/mig.db"
        return
    name = f"ems_mig_{uuid.uuid4().hex[:8]}"
    admin = create_engine(make_url(base).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield make_url(base).set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def test_upgrade_matches_models_and_downgrades_cleanly(fresh_url):
    from app.models import Base
    r = _alembic(fresh_url, "upgrade", "head")
    assert r.returncode == 0, r.stderr
    eng = create_engine(fresh_url)
    with eng.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}),
                                Base.metadata)
    assert diff == []
    tables = set(inspect(eng).get_table_names())
    assert {"organizations", "sites", "meters", "users", "readings", "ingest_batches"} <= tables
    eng.dispose()
    r = _alembic(fresh_url, "downgrade", "base")
    assert r.returncode == 0, r.stderr
    eng = create_engine(fresh_url)
    assert set(inspect(eng).get_table_names()) <= {"alembic_version"}
    eng.dispose()


def test_readings_unique_meter_ts_enforced_by_migration(fresh_url):
    assert _alembic(fresh_url, "upgrade", "head").returncode == 0
    uniques = inspect(create_engine(fresh_url)).get_unique_constraints("readings")
    assert any(set(u["column_names"]) == {"meter_id", "ts"} for u in uniques)
