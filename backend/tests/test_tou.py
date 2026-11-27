from datetime import date, datetime

import pytest

from app.services.energy import TAIPEI
from app.services.tou import classify, is_summer, load_offpeak_days


def L(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=TAIPEI)


@pytest.mark.parametrize("d,expected", [
    (date(2026, 5, 15), False), (date(2026, 5, 16), True),
    (date(2026, 10, 15), True), (date(2026, 10, 16), False),
    (date(2026, 6, 1), True), (date(2026, 1, 1), False),
])
def test_summer_months_5_16_to_10_15_inclusive(d, expected):
    assert is_summer(d) is expected


@pytest.mark.parametrize("ts,expected", [
    # 2026-05-15 is Friday, still non-summer: 11:00-14:00 off-peak
    (L(2026, 5, 15, 12), "off_peak"),
    # 2026-05-16 is Saturday, summer: 09-24 is sat_semi_peak
    (L(2026, 5, 16, 12), "sat_semi_peak"),
    # 2026-05-18 Monday summer: 12:00 is peak
    (L(2026, 5, 18, 12), "peak"),
    # 2026-10-15 Thursday last summer day: 12:00 peak
    (L(2026, 10, 15, 12), "peak"),
    # 2026-10-16 Friday non-summer: 12:00 off-peak
    (L(2026, 10, 16, 12), "off_peak"),
    # summer weekday boundaries
    (L(2026, 7, 1, 8, 59), "off_peak"), (L(2026, 7, 1, 9, 0), "peak"),
    (L(2026, 7, 1, 23, 45), "peak"), (L(2026, 7, 2, 0, 0), "off_peak"),
    # non-summer weekday: 06-11 and 14-24 peak
    (L(2026, 1, 5, 5, 45), "off_peak"), (L(2026, 1, 5, 6, 0), "peak"),
    (L(2026, 1, 5, 10, 45), "peak"), (L(2026, 1, 5, 11, 0), "off_peak"),
    (L(2026, 1, 5, 13, 45), "off_peak"), (L(2026, 1, 5, 14, 0), "peak"),
    # Saturday (2026-01-10) non-summer
    (L(2026, 1, 10, 7), "sat_semi_peak"), (L(2026, 1, 10, 12), "off_peak"),
    (L(2026, 1, 10, 3), "off_peak"),
    # Sunday 2026-01-11 all off-peak
    (L(2026, 1, 11, 10), "off_peak"), (L(2026, 7, 5, 15), "off_peak"),
])
def test_two_stage_classification(ts, expected):
    assert classify(ts, "two_stage") == expected


@pytest.mark.parametrize("ts,expected", [
    # summer weekday (2026-07-01 Wed)
    (L(2026, 7, 1, 8, 45), "off_peak"), (L(2026, 7, 1, 9, 0), "semi_peak"),
    (L(2026, 7, 1, 15, 45), "semi_peak"), (L(2026, 7, 1, 16, 0), "peak"),
    (L(2026, 7, 1, 21, 45), "peak"), (L(2026, 7, 1, 22, 0), "semi_peak"),
    (L(2026, 7, 1, 23, 45), "semi_peak"),
    # non-summer weekday (2026-01-05 Mon): no peak
    (L(2026, 1, 5, 5, 0), "off_peak"), (L(2026, 1, 5, 6, 0), "semi_peak"),
    (L(2026, 1, 5, 11, 0), "off_peak"), (L(2026, 1, 5, 14, 0), "semi_peak"),
    (L(2026, 1, 5, 18, 0), "semi_peak"),
    # Saturday / Sunday as two-stage
    (L(2026, 7, 4, 10), "sat_semi_peak"), (L(2026, 7, 4, 3), "off_peak"),
    (L(2026, 7, 5, 18), "off_peak"),
])
def test_three_stage_classification(ts, expected):
    assert classify(ts, "three_stage") == expected


def test_offpeak_day_is_all_off_peak_even_on_weekday_and_saturday():
    days = frozenset({date(2026, 7, 1), date(2026, 7, 4)})
    assert classify(L(2026, 7, 1, 12), "two_stage", days) == "off_peak"
    assert classify(L(2026, 7, 4, 12), "two_stage", days) == "off_peak"
    assert classify(L(2026, 7, 2, 12), "two_stage", days) == "peak"


def test_unsupported_schemes_raise_not_implemented():
    for scheme in ("three_stage_variable", "batch_production"):
        with pytest.raises(NotImplementedError, match="未實作|not implemented"):
            classify(L(2026, 7, 1, 12), scheme)


def test_offpeak_calendar_is_empty_until_verified():
    assert load_offpeak_days() == frozenset()
