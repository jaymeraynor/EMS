"""Admin CLI:  python -m app.cli create-admin --email ... --password ...  |  seed-demo"""
from __future__ import annotations

import argparse
import getpass
import math
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.db import get_engine


def create_admin(db: Session, email: str, password: str) -> models.User:
    email = schemas._norm_email(email)
    schemas._check_password(password)
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise ValueError(f"{email} 已存在")
    user = models.User(email=email, password_hash=security.hash_password(password),
                       role="admin", org_id=None, is_active=True)
    db.add(user)
    db.commit()
    return user


DEMO_ORG = "示範組織（模擬資料）"


def seed_demo(db: Session, days: int = 14) -> str | None:
    """Create a clearly-labelled SIMULATED meter with synthetic readings (is_demo = true).

    Returns the meter API key (shown once), or None if the demo org already exists.
    """
    if db.scalar(select(models.Organization).where(models.Organization.name == DEMO_ORG)):
        return None
    org = models.Organization(name=DEMO_ORG)
    db.add(org)
    db.flush()
    site = models.Site(org_id=org.id, name="示範案場（模擬）")
    db.add(site)
    db.flush()
    key = security.generate_api_key()
    meter = models.Meter(
        site_id=site.id, name="示範電表（模擬資料）", is_demo=True, voltage="high", scheme="two_stage",
        contract_regular_kw=200, contract_sat_semi_peak_kw=100, contract_off_peak_kw=100,
        customer_category="industrial", api_key_hash=security.hash_api_key(key), api_key_prefix=key[:8])
    db.add(meter)
    db.flush()
    step = timedelta(minutes=5)
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end -= timedelta(minutes=end.minute % 5)
    t = end - timedelta(days=days)
    kwh = kvarh = 0.0
    rows = []
    while t <= end:
        hour = (t + timedelta(hours=8)).hour + (t.minute / 60)
        kw = 80 + 60 * max(0.0, math.sin((hour - 6) / 12 * math.pi)) + 5 * math.sin(t.timestamp() / 900)
        rows.append({"meter_id": meter.id, "ts": t, "power_kw": round(kw, 3),
                     "energy_kwh_total": round(kwh, 4), "kvarh_total": round(kvarh, 4),
                     "source": "api", "received_at": end})
        kwh += kw * 5 / 60
        kvarh += kw * 5 / 60 * 0.3
        t += step
    db.execute(models.Reading.__table__.insert(), rows)
    db.commit()
    return key


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ca = sub.add_parser("create-admin", help="create the first (or another) system admin")
    ca.add_argument("--email", required=True)
    ca.add_argument("--password", help="omit to be prompted (keeps it out of shell history)")
    sd = sub.add_parser("seed-demo", help="create a SIMULATED demo org/site/meter with fake readings")
    sd.add_argument("--days", type=int, default=14)
    args = ap.parse_args(argv)
    with Session(get_engine()) as db:
        if args.cmd == "create-admin":
            pw = args.password or getpass.getpass("Password: ")
            try:
                create_admin(db, args.email, pw)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            print(f"admin {args.email} created")
        else:
            key = seed_demo(db, args.days)
            print("demo already exists" if key is None else f"demo meter created (SIMULATED). API key (shown once): {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
