"""Energy integration, Taipei calendar days and 15-minute demand.

Pure functions over time-ordered ``Sample`` lists. Nothing here assumes a fixed
sampling interval: every segment is weighted by its real duration.

Rules
* A segment between two consecutive samples longer than ``max_gap_minutes`` is
  NOT integrated (reported as gap).
* Segment energy = difference of the cumulative energy register when both ends
  have one, else trapezoid of ``power_kw``. Segments are clipped to the window
  edges with linear interpolation.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional, Sequence
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")
UTC = timezone.utc
DEFAULT_MAX_GAP_MINUTES = 15
BLOCK_MINUTES = 15
_EPS = 1e-6


@dataclass(frozen=True)
class Sample:
    ts: datetime
    power_kw: float
    energy_kwh_total: Optional[float] = None
    kvarh_total: Optional[float] = None


@dataclass(frozen=True)
class WindowResult:
    start: datetime
    end: datetime
    kwh: float
    covered_seconds: float
    gap_seconds: float
    coverage: float


@dataclass(frozen=True)
class DayResult:
    date: date
    kwh: float
    coverage: float
    gap_seconds: float


@dataclass(frozen=True)
class Block:
    start: datetime          # Asia/Taipei, aligned to :00/:15/:30/:45
    kwh: float
    coverage: float
    demand_kw: float         # kWh in block x 4 (15-min average power)
    complete: bool


# --- helpers ----------------------------------------------------------------

def taipei_date(ts: datetime) -> date:
    return ts.astimezone(TAIPEI).date()


def day_window(d: date) -> tuple[datetime, datetime]:
    """UTC instants of local midnight .. next local midnight."""
    start = datetime(d.year, d.month, d.day, tzinfo=TAIPEI)
    end = datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=TAIPEI)
    return start.astimezone(UTC), end.astimezone(UTC)


def month_window(year: int, month: int) -> tuple[datetime, datetime]:
    """UTC bounds of a Taipei calendar month; ValueError if either bound is not representable."""
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    try:
        start = datetime(year, month, 1, tzinfo=TAIPEI).astimezone(UTC)
        return start, datetime(ny, nm, 1, tzinfo=TAIPEI).astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError(f"month out of supported range: {year:04d}-{month:02d}") from None


def year_window(year: int) -> tuple[datetime, datetime]:
    return (datetime(year, 1, 1, tzinfo=TAIPEI).astimezone(UTC),
            datetime(year + 1, 1, 1, tzinfo=TAIPEI).astimezone(UTC))


# --- core integration ---------------------------------------------------------

def _accumulate(samples: Sequence[Sample], edges: Sequence[datetime], max_gap_minutes: float,
                value: Callable[[Sample, Sample, float, float, float], Optional[float]]):
    """Sum ``value`` over segments clipped to each window defined by consecutive edges.

    value(a, b, f_lo, f_hi, dt_s) gets the segment and the clipped fractions
    [f_lo, f_hi] of it (0..1) and returns the amount, or None if unusable.
    Returns (totals, covered_seconds) per window.
    """
    e = [x.timestamp() for x in edges]
    n = len(e) - 1
    totals = [0.0] * n
    covered = [0.0] * n
    max_gap_s = max_gap_minutes * 60
    for a, b in zip(samples, samples[1:]):
        ta, tb = a.ts.timestamp(), b.ts.timestamp()
        dt = tb - ta
        if dt <= 0 or dt > max_gap_s + _EPS:
            continue
        i = max(bisect_right(e, ta) - 1, 0)
        while i < n and e[i] < tb:
            lo, hi = max(ta, e[i]), min(tb, e[i + 1])
            if hi > lo:
                v = value(a, b, (lo - ta) / dt, (hi - ta) / dt, dt)
                if v is not None:
                    totals[i] += v
                    covered[i] += hi - lo
            i += 1
    return totals, covered


def _kwh_value(a: Sample, b: Sample, f_lo: float, f_hi: float, dt: float) -> Optional[float]:
    if a.energy_kwh_total is not None and b.energy_kwh_total is not None:
        return max(0.0, b.energy_kwh_total - a.energy_kwh_total) * (f_hi - f_lo)
    p_lo = a.power_kw + (b.power_kw - a.power_kw) * f_lo
    p_hi = a.power_kw + (b.power_kw - a.power_kw) * f_hi
    return (p_lo + p_hi) / 2 * (f_hi - f_lo) * dt / 3600


def integrate_windows(samples: Sequence[Sample], edges: Sequence[datetime],
                      max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> list[WindowResult]:
    totals, covered = _accumulate(samples, edges, max_gap_minutes, _kwh_value)
    out = []
    for i, (kwh, cov) in enumerate(zip(totals, covered)):
        span = edges[i + 1].timestamp() - edges[i].timestamp()
        cov = min(cov, span)
        if span - cov < _EPS:
            cov = span
        out.append(WindowResult(edges[i], edges[i + 1], kwh, cov, span - cov,
                                cov / span if span else 0.0))
    return out


def integrate(samples: Sequence[Sample], start: datetime, end: datetime,
              max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> WindowResult:
    return integrate_windows(samples, [start, end], max_gap_minutes)[0]


def register_total(samples: Sequence[Sample], start: datetime, end: datetime, field: str,
                   max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> float:
    """Register increase (e.g. kvarh_total) inside the window, same gap rules as kWh."""
    return register_total_covered(samples, start, end, field, max_gap_minutes)[0]


def register_total_covered(samples: Sequence[Sample], start: datetime, end: datetime, field: str,
                           max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> tuple[float, float]:
    """(register increase, covered seconds) inside the window.

    Covered seconds count only segments whose two ends both carry the register and
    that are not longer than the gap limit, so callers can tell "measured zero" from
    "not measured".
    """
    def val(a: Sample, b: Sample, f_lo: float, f_hi: float, dt: float) -> Optional[float]:
        ra, rb = getattr(a, field), getattr(b, field)
        if ra is None or rb is None:
            return None
        return max(0.0, rb - ra) * (f_hi - f_lo)
    totals, covered = _accumulate(samples, [start, end], max_gap_minutes, val)
    return totals[0], covered[0]


# --- days and demand ------------------------------------------------------------

def daily_kwh(samples: Sequence[Sample], first_day: date, last_day: date,
              max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> list[DayResult]:
    """kWh per Asia/Taipei calendar day, first_day..last_day inclusive."""
    days, edges = [], []
    d = first_day
    while d <= last_day:
        days.append(d)
        edges.append(day_window(d)[0])
        d += timedelta(days=1)
    edges.append(day_window(last_day)[1])
    res = integrate_windows(samples, edges, max_gap_minutes)
    return [DayResult(d, r.kwh, r.coverage, r.gap_seconds) for d, r in zip(days, res)]


def blocks_between(samples: Sequence[Sample], start: datetime, end: datetime,
                   max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> list[Block]:
    """15-minute blocks from ``start`` to ``end`` (both must be on a block boundary)."""
    step = timedelta(minutes=BLOCK_MINUTES)
    edges, t = [], start
    while t < end:
        edges.append(t)
        t += step
    edges.append(end)
    res = integrate_windows(samples, edges, max_gap_minutes)
    return [Block(r.start.astimezone(TAIPEI), r.kwh, r.coverage, r.kwh * 4, r.coverage >= 1.0)
            for r in res]


def demand_blocks(samples: Sequence[Sample], day: date,
                  max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> list[Block]:
    start, end = day_window(day)
    return blocks_between(samples, start, end, max_gap_minutes)
