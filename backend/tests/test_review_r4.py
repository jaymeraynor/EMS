"""Regression tests for code-review round 4 (codex-r4-findings)."""
import re
import subprocess
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.test_ingest import post, rd

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


# --- 1. login form must never fall back to GET -------------------------------------------
class _Forms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms, self._cur = [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self._cur = {"attrs": a, "inputs": [], "buttons": []}
            self.forms.append(self._cur)
        elif self._cur is not None and tag == "input":
            self._cur["inputs"].append(a)
        elif self._cur is not None and tag == "button":
            self._cur["buttons"].append(a)

    def handle_endtag(self, tag):
        if tag == "form":
            self._cur = None


def test_login_form_posts_and_has_password_inside():
    p = _Forms()
    p.feed((FRONTEND / "index.html").read_text(encoding="utf-8"))
    form = next(f for f in p.forms if f["attrs"].get("id") == "login-form")
    assert form["attrs"].get("method", "").lower() == "post"
    assert any(i.get("type") == "password" for i in form["inputs"])
    # submit stays disabled until app.js installs the handler
    assert any("disabled" in b for b in form["buttons"])
    assert "disabled" in (FRONTEND / "assets" / "app.js").read_text(encoding="utf-8")


# --- 2. SQLite: validation + write serialised across connections ------------------------
def test_sqlite_concurrent_uploads_are_serialised(engine, world, meter_a, monkeypatch):
    if engine.dialect.name != "sqlite":
        pytest.skip("PostgreSQL is covered by the row-lock test")
    from sqlalchemy.orm import Session

    from app import models
    from app.services import ingest
    from app.schemas import ReadingIn

    meter_id = meter_a[0]["id"]
    orig = ingest._register_errors

    def slow(*a, **k):
        r = orig(*a, **k)
        time.sleep(1.0)       # widen the validate -> write window
        return r

    monkeypatch.setattr(ingest, "_register_errors", slow)
    out = {}

    def upload(name, ts, kwh, delay):
        time.sleep(delay)
        with Session(engine, expire_on_commit=False) as s:
            m = s.get(models.Meter, meter_id)
            try:
                out[name] = ingest.store_readings(
                    s, m, [ReadingIn(ts=ts, power_kw=1, energy_kwh_total=kwh)], "api")
            except ingest.IngestRejected as e:
                out[name] = e

    ta = threading.Thread(target=upload, args=("a", "2026-01-01T00:00:00+00:00", 100, 0))
    tb = threading.Thread(target=upload, args=("b", "2026-01-01T01:00:00+00:00", 50, 0.3))
    ta.start(); tb.start(); ta.join(); tb.join()
    assert out["a"]["inserted"] == 1
    assert isinstance(out["b"], ingest.IngestRejected), out


# --- 3. partial indexes for neighbour lookups --------------------------------------------
IDX = {"ix_readings_meter_ts_kwh_notnull": "energy_kwh_total",
       "ix_readings_meter_ts_kvarh_notnull": "kvarh_total"}


def test_partial_indexes_in_metadata():
    from app.models import Reading
    names = {i.name: i for i in Reading.__table__.indexes}
    for n, col in IDX.items():
        assert n in names, n
        assert [c.name for c in names[n].columns] == ["meter_id", "ts"]
        for d in ("postgresql", "sqlite"):
            w = names[n].dialect_options[d]["where"]
            assert w is not None and str(w).replace('"', "") == f"{col} IS NOT NULL"


def test_partial_indexes_exist_after_migration(tmp_path):
    from sqlalchemy import create_engine
    from tests.test_alembic import _alembic
    url = f"sqlite:///{tmp_path}/m.db"
    assert _alembic(url, "upgrade", "head").returncode == 0
    eng = create_engine(url)
    with eng.connect() as c:
        rows = {r[0]: r[1] for r in c.execute(text(
            "select name, sql from sqlite_master where type='index' and tbl_name='readings'"))}
    for n, col in IDX.items():
        assert n in rows and f"{col} IS NOT NULL" in rows[n], rows
    eng.dispose()
    assert _alembic(url, "downgrade", "0001").returncode == 0
    eng = create_engine(url)
    with eng.connect() as c:
        left = {r[0] for r in c.execute(text(
            "select name from sqlite_master where type='index' and tbl_name='readings'"))}
    assert not (set(IDX) & left)
    eng.dispose()


def test_neighbour_query_uses_partial_index_on_sqlite(engine):
    if engine.dialect.name != "sqlite":
        pytest.skip("sqlite plan check")
    from sqlalchemy import select
    from app.models import Reading as R
    from app.services.ingest import REGISTERS
    for field, n in (("energy_kwh_total", "ix_readings_meter_ts_kwh_notnull"),
                     ("kvarh_total", "ix_readings_meter_ts_kvarh_notnull")):
        assert field in REGISTERS
        col = getattr(R, field)
        from datetime import datetime, timezone
        q = select(R.ts, col).where(R.meter_id == 1, col.is_not(None),
                                    R.ts < datetime(2026, 1, 1, tzinfo=timezone.utc)
                                    ).order_by(R.ts.desc()).limit(1)
        sql = str(q.compile(engine, compile_kwargs={"literal_binds": True}))
        # INDEXED BY errors out ("no query solution") unless the query implies the partial predicate
        sql = sql.replace("FROM readings", f"FROM readings INDEXED BY {n}", 1)
        with engine.connect() as c:
            plan = " ".join(str(r) for r in c.execute(text("EXPLAIN QUERY PLAN " + sql)))
        assert n in plan, plan


# --- 4. upper bounds on contract capacity / coefficient ----------------------------------
MAX_KW, MAX_COEF = 1e6, 10
CONTRACT_FIELDS = ["contract_regular_kw", "contract_non_summer_kw", "contract_semi_peak_kw",
                   "contract_sat_semi_peak_kw", "contract_off_peak_kw"]


def test_max_allowed_values_bill_ok(client, world):
    body = {"site_id": world.site_a.id, "name": "BIG", "industry_adjustment_coef": MAX_COEF,
            **{f: MAX_KW for f in CONTRACT_FIELDS}}
    r = client.post("/api/v1/meters", headers=world.h_oa_a, json=body)
    assert r.status_code == 201, r.text
    key = r.json()["api_key"]
    mid = r.json()["id"]
    items = [rd(f"2026-07-01T{h:02d}:00:00+08:00", 1e7, energy_kwh_total=h * 1e7)
             for h in range(0, 24)]
    assert post(client, key, items).status_code == 200
    for scheme in ("two_stage", "three_stage"):
        assert client.patch(f"/api/v1/meters/{mid}", headers=world.h_oa_a,
                            json={"scheme": scheme}).status_code == 200
        b = client.get(f"/api/v1/meters/{mid}/bill?month=2026-07", headers=world.h_oa_a)
        assert b.status_code == 200, b.text


@pytest.mark.parametrize("field,val", [(f, MAX_KW * 1.0001) for f in CONTRACT_FIELDS]
                         + [("industry_adjustment_coef", MAX_COEF + 0.01)])
def test_values_above_bounds_rejected(client, world, meter_a, field, val):
    r = client.post("/api/v1/meters", headers=world.h_oa_a,
                    json={"site_id": world.site_a.id, "name": "X", field: val})
    assert r.status_code == 422
    r = client.patch(f"/api/v1/meters/{meter_a[0]['id']}", headers=world.h_oa_a, json={field: val})
    assert r.status_code == 422


# --- 5. org Scope 2 totals exclude demo meters -------------------------------------------
def test_org_scope2_totals_exclude_demo(client, world):
    keys = {}
    for name, demo in (("real", False), ("demo", True)):
        r = client.post("/api/v1/meters", headers=world.h_oa_a,
                        json={"site_id": world.site_a.id, "name": name, "is_demo": demo})
        assert r.status_code == 201, r.text
        keys[name] = (r.json()["id"], r.json()["api_key"])
    for name, p in (("real", 100.0), ("demo", 500.0)):
        items = [rd(f"2026-03-01T{h:02d}:{m:02d}:00+08:00", p) for h in range(0, 3) for m in range(60)]
        assert post(client, keys[name][1], items).status_code == 200
    r = client.get(f"/api/v1/orgs/{world.org_a.id}/scope2?year=2026", headers=world.h_oa_a)
    assert r.status_code == 200, r.text
    j = r.json()
    rows = {m["name"]: m for m in j["meters"]}
    assert rows["demo"]["kwh"] > rows["real"]["kwh"] > 0
    assert j["kwh"] == pytest.approx(rows["real"]["kwh"])
    assert j["scope2_tco2e"] == pytest.approx(rows["real"]["scope2_tco2e"], abs=1e-3)
    assert j["simulated_total_kwh"] == pytest.approx(rows["demo"]["kwh"])
    assert j["simulated_total_emissions"] == pytest.approx(rows["demo"]["scope2_tco2e"], abs=1e-3)


# --- 6. out-of-range instants are validation errors, not 500s ----------------------------
@pytest.mark.parametrize("ts", ["0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"])
def test_extreme_timestamp_json_is_422(client, meter_a, ts):
    r = post(client, meter_a[1], [rd(ts)])
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("ts", ["0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"])
def test_extreme_timestamp_csv_is_row_error(client, world, meter_a, ts):
    from tests.test_csv import upload
    r = upload(client, world.h_oa_a, meter_a[0]["id"], f"ts,power_kw\n{ts},1\n".encode())
    assert r.status_code == 422, r.text
    assert "2" in str(r.json())


def test_reading_validator_normalises_to_utc():
    from app.schemas import ReadingIn
    r = ReadingIn(ts="2026-07-01T08:00:00+08:00", power_kw=1)
    assert r.ts.utcoffset().total_seconds() == 0 and r.ts.hour == 0


# --- 7. frontend: no native append(null) -------------------------------------------------
def test_frontend_append_null_guard():
    script = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const log = [];
class Node_ { constructor(t){this.tag=t;this.children=[];this.dataset={};this.firstChild=null;}
  append(...a){ for (const x of a) this.children.push(x === null ? 'null' : x); }
  setAttribute(){} addEventListener(){} removeChild(){} set textContent(v){} }
global.Node = Node_;
global.document = { createElement: t => new Node_(t), createTextNode: s => ({text:String(s)}),
  addEventListener(){}, body: {dataset:{}}, querySelector: () => new Node_('x') };
global.sessionStorage = {getItem(){return null}, setItem(){}};
global.location = {}; global.window = global;
const code = src + "\n;globalThis.__t = {renderCarbon, renderBill, $};";
(0, eval)(code.replace('"use strict";',''));
const host = new Node_('div'); const orig = document.querySelector;
document.querySelector = () => host;
__t.renderCarbon({year:2026,is_demo:false,scope2_tco2e:1,kwh:1,coverage:1,factor_kg_per_kwh:0.5,
  factor_year:2026,customer_category:'industrial',provisional:false,warnings:[]});
if (host.children.includes('null')) { console.error('null appended'); process.exit(1); }
"""
    r = subprocess.run(["node", "-e", script, str(FRONTEND / "assets" / "app.js")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
