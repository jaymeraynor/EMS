"""Test helpers: build reading series from simple descriptions."""
from datetime import datetime, timedelta, timezone

from app.services.energy import Sample

UTC = timezone.utc


def utc(s: str) -> datetime:
    """'2026-07-01T16:30' (UTC) -> aware datetime. Accepts trailing Z."""
    return datetime.fromisoformat(s.replace("Z", "")).replace(tzinfo=UTC)


def grid(start: datetime, end: datetime, step_min: int, power_kw=100.0, with_registers=False,
         kvarh_ratio=None):
    """Samples every step_min from start to end inclusive at constant power.

    with_registers: also fill cumulative energy_kwh_total consistent with power.
    kvarh_ratio: if set, kvarh_total grows at ratio * kWh.
    """
    out = []
    t = start
    kwh = 0.0
    kvarh = 0.0
    step_h = step_min / 60
    while t <= end:
        p = power_kw(t) if callable(power_kw) else power_kw
        out.append(Sample(
            ts=t, power_kw=p,
            energy_kwh_total=kwh if with_registers else None,
            kvarh_total=kvarh if kvarh_ratio is not None else None,
        ))
        kwh += p * step_h
        if kvarh_ratio is not None:
            kvarh += p * step_h * kvarh_ratio
        t += timedelta(minutes=step_min)
    return out
