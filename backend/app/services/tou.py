"""Time-of-use period classification for Taipower high / extra-high voltage.

Rules: regs §2.2 (summer = 5/16-10/15 inclusive). A 15-min block or reading
segment is classified by its START time (TOU boundaries are on the hour).
"""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

PEAK, SEMI_PEAK, SAT_SEMI_PEAK, OFF_PEAK = "peak", "semi_peak", "sat_semi_peak", "off_peak"


def is_summer(d: date) -> bool:
    """High-voltage summer: 5/16 .. 10/15 inclusive."""
    return (5, 16) <= (d.month, d.day) <= (10, 15)


@lru_cache(maxsize=1)
def load_offpeak_days() -> frozenset[date]:
    # TODO: calendar not verified, file is empty (see offpeak_days.yaml)
    raw = yaml.safe_load((DATA_DIR / "offpeak_days.yaml").read_text(encoding="utf-8")) or {}
    return frozenset(date.fromisoformat(str(x)) for x in (raw.get("days") or []))


def _in(hour: int, *ranges: tuple[int, int]) -> bool:
    return any(a <= hour < b for a, b in ranges)


def classify(ts_local: datetime, scheme: str,
             offpeak_days: frozenset[date] = frozenset()) -> str:
    """Return the TOU period name for a local (Asia/Taipei) timestamp."""
    if scheme not in ("two_stage", "three_stage"):
        raise NotImplementedError(
            f"計費方式 {scheme!r} 尚未實作 (not implemented): 僅支援 two_stage / three_stage（尖峰時間固定）")
    d, h = ts_local.date(), ts_local.hour
    wd = ts_local.weekday()  # Mon=0 .. Sun=6
    summer = is_summer(d)
    if wd == 6 or d in offpeak_days:
        return OFF_PEAK
    if wd == 5:  # Saturday: same hours as two-stage peak become sat_semi_peak
        hours = [(9, 24)] if summer else [(6, 11), (14, 24)]
        return SAT_SEMI_PEAK if _in(h, *hours) else OFF_PEAK
    if scheme == "two_stage":
        hours = [(9, 24)] if summer else [(6, 11), (14, 24)]
        return PEAK if _in(h, *hours) else OFF_PEAK
    # three_stage, fixed peak, weekday
    if summer:
        if _in(h, (16, 22)):
            return PEAK
        return SEMI_PEAK if _in(h, (9, 16), (22, 24)) else OFF_PEAK
    return SEMI_PEAK if _in(h, (6, 11), (14, 24)) else OFF_PEAK
