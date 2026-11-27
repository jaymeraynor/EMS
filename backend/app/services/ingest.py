"""Validated, idempotent storage of readings (shared by the ingest API and CSV import)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.schemas import ReadingIn

REGISTERS = ("energy_kwh_total", "kvarh_total")
_TOL = 1e-9


class IngestRejected(Exception):
    """Batch refused; ``errors`` is a list of {"index": int, "error": str} (0-based item index)."""

    def __init__(self, errors: list[dict]):
        super().__init__(f"{len(errors)} invalid item(s)")
        self.errors = errors


def _utc(ts: datetime) -> datetime:
    return ts.astimezone(timezone.utc)


def _register_errors(db: Session, meter_id: int, fresh: list[tuple[int, ReadingIn]]) -> list[dict]:
    """Cumulative registers must not decrease along time (vs stored readings and inside the batch)."""
    if not fresh:
        return []
    R = models.Reading
    errors: dict[int, str] = {}
    for field in REGISTERS:
        col = getattr(R, field)
        if not any(getattr(r, field) is not None for _, r in fresh):
            continue
        base = select(R.ts, col).where(R.meter_id == meter_id, col.is_not(None))
        points: list[tuple[datetime, float, int | None]] = []   # (ts, value, item index or None)
        # Only the stored readings adjacent (in time) to an incoming one can matter, so look up the
        # nearest stored value on each side of every incoming point instead of loading the span.
        seen_rows: set[datetime] = set()

        def add(row):
            if row[0] not in seen_rows:
                seen_rows.add(row[0])
                points.append((row[0], row[1], None))

        for idx, r in fresh:
            if getattr(r, field) is None:
                continue
            t = _utc(r.ts)
            for row in db.execute(base.where(R.ts < t).order_by(R.ts.desc()).limit(1)):
                add(row)
            for row in db.execute(base.where(R.ts > t).order_by(R.ts).limit(1)):
                add(row)
        for idx, r in fresh:
            v = getattr(r, field)
            if v is not None:
                points.append((_utc(r.ts), v, idx))
        points.sort(key=lambda p: p[0])
        last_val, last_idx = None, None
        for _ts, val, idx in points:
            if last_val is not None and val < last_val - _TOL:
                if idx is not None:       # this new item is below an earlier reading
                    msg = f"{field} {val} is lower than the earlier value {last_val}"
                    culprit = idx
                else:                     # an earlier new item is above a later stored reading
                    msg = f"{field} {last_val} is higher than the later stored value {val}"
                    culprit = last_idx
                if culprit is not None and culprit not in errors:
                    errors[culprit] = msg
                if idx is not None:
                    continue  # keep comparing later items against the last good value
            last_val, last_idx = val, idx
    return [{"index": i, "error": e} for i, e in sorted(errors.items())]


def store_readings(db: Session, meter: models.Meter, items: Sequence[ReadingIn], source: str,
                   user_id: int | None = None) -> dict:
    """Insert new readings; duplicates (same meter+ts) are skipped and counted."""
    for attempt in (1, 2):
        try:
            return _store_once(db, meter, items, source, user_id)
        except IntegrityError:   # concurrent insert of the same ts: recompute duplicates once
            db.rollback()
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


def _lock_meter(db: Session, meter_id: int) -> None:
    """Serialise writers per meter: hold the meter row lock until commit/rollback.

    The cumulative-register check reads existing readings, so two concurrent batches
    could otherwise each validate against the same committed data and together break
    monotonicity. SELECT ... FOR UPDATE is a no-op on SQLite (single writer anyway).
    """
    db.execute(select(models.Meter.id).where(models.Meter.id == meter_id).with_for_update())


def _store_once(db, meter, items, source, user_id) -> dict:
    _lock_meter(db, meter.id)
    received = len(items)
    seen: set[datetime] = set()
    fresh: list[tuple[int, ReadingIn]] = []
    for idx, r in enumerate(items):
        key = _utc(r.ts)
        if key in seen:
            continue
        seen.add(key)
        fresh.append((idx, r))
    existing: set[datetime] = set()    # exact-timestamp lookup: cost follows the batch, not the history
    wanted = list(seen)
    for i in range(0, len(wanted), 500):
        existing.update(_utc(t) for t in db.scalars(select(models.Reading.ts).where(
            models.Reading.meter_id == meter.id, models.Reading.ts.in_(wanted[i:i + 500]))))
    fresh = [(i, r) for i, r in fresh if _utc(r.ts) not in existing]

    errors = _register_errors(db, meter.id, fresh)
    if errors:
        raise IngestRejected(errors)

    now = datetime.now(timezone.utc)
    if fresh:
        db.execute(insert(models.Reading), [
            {"meter_id": meter.id, "ts": _utc(r.ts), "power_kw": r.power_kw,
             "energy_kwh_total": r.energy_kwh_total, "kvarh_total": r.kvarh_total,
             "source": source, "received_at": now} for _, r in fresh])
    inserted = len(fresh)
    db.add(models.IngestBatch(meter_id=meter.id, source=source, user_id=user_id, received=received,
                              inserted=inserted, duplicates=received - inserted))
    db.commit()
    return {"received": received, "inserted": inserted, "duplicates": received - inserted}
