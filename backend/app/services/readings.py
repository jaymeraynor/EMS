"""Database access for calculation services."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.services.energy import Sample


def load_samples(db: Session, meter_id: int, start: datetime, end: datetime) -> list[Sample]:
    """Readings covering [start, end] plus one max-gap margin on each side (bounding samples)."""
    pad = timedelta(minutes=get_settings().max_gap_minutes)
    R = models.Reading
    rows = db.execute(
        select(R.ts, R.power_kw, R.energy_kwh_total, R.kvarh_total)
        .where(R.meter_id == meter_id, R.ts >= start - pad, R.ts <= end + pad)
        .order_by(R.ts))
    return [Sample(ts, p, e, k) for ts, p, e, k in rows]
