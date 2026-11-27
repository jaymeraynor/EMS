from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.energy import (
    Sample, TAIPEI, daily_kwh, demand_blocks, integrate, taipei_date, register_total,
)
from tests.helpers import grid, utc


def S(ts, p, e=None, k=None):
    return Sample(ts=utc(ts), power_kw=p, energy_kwh_total=e, kvarh_total=k)


# --- kWh integration -------------------------------------------------------

def test_constant_power_one_hour():
    # 60 kW for 1 h = 60 kWh
    r = integrate(grid(utc("2026-01-01T00:00"), utc("2026-01-01T01:00"), 5, 60.0),
                  utc("2026-01-01T00:00"), utc("2026-01-01T01:00"))
    assert r.kwh == pytest.approx(60.0)
    assert r.coverage == pytest.approx(1.0)
    assert r.gap_seconds == 0


def test_mixed_2s_and_5min_intervals_regression_vs_sum_div_3600():
    # Old demo did sum(power)/3600 (assumes 1 s samples). 100 kW for 606 s
    # is 100*606/3600 = 16.8333 kWh; the old method would give 6*100/3600=0.1667.
    samples = [
        S("2026-01-01T00:00:00", 100), S("2026-01-01T00:00:02", 100),
        S("2026-01-01T00:00:04", 100), S("2026-01-01T00:00:06", 100),
        S("2026-01-01T00:05:06", 100), S("2026-01-01T00:10:06", 100),
    ]
    r = integrate(samples, utc("2026-01-01T00:00:00"), utc("2026-01-01T00:10:06"))
    assert r.kwh == pytest.approx(100 * 606 / 3600)
    assert r.kwh != pytest.approx(sum(s.power_kw for s in samples) / 3600)


def test_gap_longer_than_max_is_not_integrated_and_reported():
    # readings 00:00,00:10 | gap 30 min | 00:40,00:50 ; window 1 h at 60 kW
    samples = [S("2026-01-01T00:00", 60), S("2026-01-01T00:10", 60),
               S("2026-01-01T00:40", 60), S("2026-01-01T00:50", 60)]
    r = integrate(samples, utc("2026-01-01T00:00"), utc("2026-01-01T01:00"),
                  max_gap_minutes=15)
    assert r.kwh == pytest.approx(20.0)            # 20 min covered at 60 kW
    assert r.gap_seconds == 40 * 60                # 30 min gap + 10 min tail
    assert r.coverage == pytest.approx(20 / 60)


def test_segment_exactly_max_gap_is_integrated():
    samples = [S("2026-01-01T00:00", 60), S("2026-01-01T00:15", 60)]
    r = integrate(samples, utc("2026-01-01T00:00"), utc("2026-01-01T00:15"),
                  max_gap_minutes=15)
    assert r.kwh == pytest.approx(15.0)
    assert r.coverage == pytest.approx(1.0)


def test_window_clips_with_linear_interpolation():
    # power ramps 0 -> 120 kW over 10 min. Window 5..10 min: p from 60 to 120,
    # avg 90 kW over 5 min = 7.5 kWh
    samples = [S("2026-01-01T00:00", 0), S("2026-01-01T00:10", 120)]
    r = integrate(samples, utc("2026-01-01T00:05"), utc("2026-01-01T00:10"))
    assert r.kwh == pytest.approx(7.5)


def test_register_difference_preferred_and_interpolated_at_edges():
    # registers say 1.0 kWh over 10 min even though power says 999 kW
    samples = [S("2026-01-01T00:00", 999, e=100.0), S("2026-01-01T00:10", 999, e=101.0)]
    full = integrate(samples, utc("2026-01-01T00:00"), utc("2026-01-01T00:10"))
    half = integrate(samples, utc("2026-01-01T00:00"), utc("2026-01-01T00:05"))
    assert full.kwh == pytest.approx(1.0)
    assert half.kwh == pytest.approx(0.5)


def test_falls_back_to_power_when_one_register_missing():
    samples = [S("2026-01-01T00:00", 60, e=100.0), S("2026-01-01T00:10", 60, e=None)]
    r = integrate(samples, utc("2026-01-01T00:00"), utc("2026-01-01T00:10"))
    assert r.kwh == pytest.approx(10.0)  # 60 kW * 10 min


def test_no_samples_is_zero_coverage():
    r = integrate([], utc("2026-01-01T00:00"), utc("2026-01-01T01:00"))
    assert (r.kwh, r.coverage, r.gap_seconds) == (0.0, 0.0, 3600)


def test_register_total_for_kvarh():
    samples = [S("2026-01-01T00:00", 1, k=10.0), S("2026-01-01T00:10", 1, k=14.0)]
    assert register_total(samples, utc("2026-01-01T00:00"), utc("2026-01-01T00:10"),
                          "kvarh_total") == pytest.approx(4.0)


# --- Taipei days -------------------------------------------------------------

def test_taipei_date_boundary():
    # 16:30Z on 07-01 is 00:30 on 07-02 in Taipei (UTC+8)
    assert taipei_date(utc("2026-07-01T16:30")) == date(2026, 7, 2)
    assert taipei_date(utc("2026-07-01T15:59")) == date(2026, 7, 1)


def test_daily_kwh_uses_local_midnight_windows():
    samples = grid(utc("2026-07-01T15:00"), utc("2026-07-02T16:00"), 15, 120.0)
    days = daily_kwh(samples, date(2026, 7, 1), date(2026, 7, 2))
    d1, d2 = days
    assert d1.date == date(2026, 7, 1)
    # data begins 15:00Z = 23:00 Taipei -> only the last hour of 07-01
    assert d1.kwh == pytest.approx(120.0)
    assert d1.coverage == pytest.approx(1 / 24)
    # 07-02 Taipei = 07-01T16:00Z .. 07-02T16:00Z, fully covered
    assert d2.kwh == pytest.approx(120.0 * 24)
    assert d2.coverage == pytest.approx(1.0)


def test_energy_in_first_half_hour_after_utc_16_belongs_to_next_taipei_day():
    samples = [S("2026-07-01T16:00", 100), S("2026-07-01T16:15", 100),
               S("2026-07-01T16:30", 100)]
    d1, d2 = daily_kwh(samples, date(2026, 7, 1), date(2026, 7, 2))
    assert d1.kwh == 0.0
    assert d2.kwh == pytest.approx(50.0)


# --- 15-minute demand --------------------------------------------------------

def test_demand_blocks_cover_day_aligned_and_flag_incomplete():
    # Taipei 00:10..01:00 at 80 kW (= 16:10Z..17:00Z previous UTC day)
    samples = grid(utc("2026-07-01T16:10"), utc("2026-07-01T17:00"), 5, 80.0)
    blocks = demand_blocks(samples, date(2026, 7, 2))
    assert len(blocks) == 96
    assert blocks[0].start == datetime(2026, 7, 2, 0, 0, tzinfo=TAIPEI)
    assert blocks[1].start == datetime(2026, 7, 2, 0, 15, tzinfo=TAIPEI)
    b0, b1 = blocks[0], blocks[1]
    # block 00:00-00:15 has data only 00:10-00:15 -> 80 kW * 5 min = 6.6667 kWh
    assert b0.kwh == pytest.approx(80 * 5 / 60)
    assert b0.demand_kw == pytest.approx(80 * 5 / 60 * 4)
    assert b0.coverage == pytest.approx(5 / 15)
    assert b0.complete is False
    # block 00:15-00:30 complete: 20 kWh -> demand 80 kW
    assert b1.complete is True
    assert b1.kwh == pytest.approx(20.0)
    assert b1.demand_kw == pytest.approx(80.0)
    assert blocks[4].complete is False  # 01:00-01:15 has no data
    assert blocks[4].coverage == 0.0


def test_instantaneous_spike_is_not_demand():
    # 15-min block with 1 kW except a 1-minute spike of 500 kW
    samples = [S("2026-07-01T16:00", 1), S("2026-07-01T16:05", 1),
               S("2026-07-01T16:06", 500), S("2026-07-01T16:07", 1),
               S("2026-07-01T16:15", 1)]
    b0 = demand_blocks(samples, date(2026, 7, 2))[0]
    # trapezoid: 5min@1 + 1min avg 250.5 + 1min avg 250.5 + 8min@1 = 13 min @1 +
    # 501 kW*min  -> (13 + 501)/60 kWh = 8.5667 ; demand = x4 = 34.27 kW (<< 500)
    assert b0.demand_kw == pytest.approx((13 + 501) / 60 * 4)
    assert b0.demand_kw < 100
