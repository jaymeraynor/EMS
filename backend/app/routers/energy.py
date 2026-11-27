from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.deps import DB, CurrentUser, MeterOfUser, get_site_for
from app import models
from sqlalchemy import select
from app.services import tou
from app.services.energy import (
    TAIPEI, blocks_between, day_window, daily_kwh, demand_blocks,
)
from app.services.readings import load_samples

router = APIRouter(tags=["energy"])
MAX_DAILY_RANGE_DAYS = 400


def _window(d: date):
    """Taipei-day UTC window; 422 for dates whose window cannot be represented."""
    try:
        return day_window(d)
    except (ValueError, OverflowError):
        raise HTTPException(422, f"日期超出支援範圍: {d.isoformat()}") from None


def _block_json(b) -> dict:
    return {"start": b.start.isoformat(), "kwh": b.kwh, "demand_kw": b.demand_kw,
            "coverage": b.coverage, "complete": b.complete}


@router.get("/meters/{meter_id}/daily")
def daily(meter: MeterOfUser, db: DB, start: date, end: date):
    if end < start:
        raise HTTPException(422, "end 不可早於 start")
    if (end - start).days + 1 > MAX_DAILY_RANGE_DAYS:
        raise HTTPException(422, f"範圍最多 {MAX_DAILY_RANGE_DAYS} 天")
    lo, hi = _window(start)[0], _window(end)[1]
    samples = load_samples(db, meter.id, lo, hi)
    days = daily_kwh(samples, start, end, get_settings().max_gap_minutes)
    return [{"date": d.date.isoformat(), "kwh": d.kwh, "coverage": d.coverage,
             "gap_seconds": d.gap_seconds} for d in days]


@router.get("/meters/{meter_id}/demand")
def demand(meter: MeterOfUser, db: DB, date: date):
    """15-minute demand blocks for one Taipei day. Max demand uses complete blocks only."""
    lo, hi = _window(date)
    samples = load_samples(db, meter.id, lo, hi)
    blocks = demand_blocks(samples, date, get_settings().max_gap_minutes)
    complete = [b for b in blocks if b.complete]
    return {
        "date": date.isoformat(),
        "blocks": [_block_json(b) for b in blocks],
        "max_demand_kw": max((b.demand_kw for b in complete), default=0.0),
        "incomplete_blocks": len(blocks) - len(complete),
        "kwh": sum(b.kwh for b in blocks),
    }


@router.get("/sites/{site_id}/summary")
def site_summary(site_id: int, db: DB, user: CurrentUser, date: date):
    """Site totals; simultaneous demand = per-block sum across meters, then the max over blocks."""
    site = get_site_for(db, user, site_id)
    meters = db.scalars(select(models.Meter).where(models.Meter.site_id == site.id)
                        .order_by(models.Meter.id)).all()
    lo, hi = _window(date)
    gap = get_settings().max_gap_minutes
    per_meter, sums, all_complete = [], None, None
    for m in meters:
        blocks = demand_blocks(load_samples(db, m.id, lo, hi), date, gap)
        per_meter.append({"meter_id": m.id, "name": m.name, "is_demo": m.is_demo,
                          "kwh": sum(b.kwh for b in blocks),
                          "coverage": sum(b.coverage for b in blocks) / len(blocks)})
        if sums is None:
            sums = [0.0] * len(blocks)
            all_complete = [True] * len(blocks)
        for i, b in enumerate(blocks):
            sums[i] += b.demand_kw
            all_complete[i] = all_complete[i] and b.complete
    sums, all_complete = sums or [], all_complete or []
    valid = [(s, i) for i, (s, c) in enumerate(zip(sums, all_complete)) if c]
    peak = max(valid, default=(0.0, None))
    return {
        "site_id": site.id, "date": date.isoformat(), "meters": per_meter,
        "kwh": sum(m["kwh"] for m in per_meter),
        "max_simultaneous_demand_kw": peak[0],
        "max_demand_block_start": (lo.astimezone(TAIPEI) + timedelta(minutes=15 * peak[1])).isoformat()
        if peak[1] is not None else None,
        "incomplete_blocks": len(all_complete) - sum(all_complete),
    }
