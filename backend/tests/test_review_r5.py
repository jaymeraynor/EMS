"""Regression tests for code-review round 5 (codex-r5-findings)."""
import pytest

from app.services.billing import Contracts, over_contract
from tests.test_bill import _by_period, rates


def _two(summer, demand, c):
    return _by_period(over_contract("two_stage", summer, demand, c,
                                    rates("high", "two_stage", summer).basic))


@pytest.mark.parametrize("summer", [True, False])
def test_two_stage_sat_offpeak_thresholds_include_non_summer(summer):
    # reg 100, ns 20, sat 20, off 10: sat cum 140, off cum 150 in BOTH seasons
    c = Contracts(100, 20, 0, 20, 10)
    items = _two(summer, {"peak": 0, "sat_semi_peak": 130, "off_peak": 145}, c)
    assert items["sat_semi_peak"].cumulative_contract_kw == pytest.approx(140)
    assert items["off_peak"].cumulative_contract_kw == pytest.approx(150)
    assert items["sat_semi_peak"].amount == 0
    assert items["off_peak"].amount == 0


def test_two_stage_peak_threshold_unchanged_by_fix():
    c = Contracts(100, 20, 0, 20, 10)
    assert _two(True, {}, c)["peak"].cumulative_contract_kw == pytest.approx(100)
    assert _two(False, {}, c)["peak"].cumulative_contract_kw == pytest.approx(120)


def test_two_stage_summer_sat_excess_and_tier_split_use_full_cumulative():
    # sat demand 160 vs cum 140 -> raw 20 ; 10% of 140 = 14 -> 14 @2x, 6 @3x
    c = Contracts(100, 20, 0, 20, 10)
    it = _two(True, {"peak": 0, "sat_semi_peak": 160}, c)["sat_semi_peak"]
    assert (it.raw_excess_kw, it.excess_kw) == (pytest.approx(20), pytest.approx(20))
    assert (it.tier1_kw, it.tier2_kw) == (pytest.approx(14), pytest.approx(6))


def test_two_stage_non_duplication_uses_raw_excess_of_higher_priority():
    # summer peak 130 -> raw 30 ; sat 160 -> raw 20 (<30) -> net 0 ; off 170 vs 150 -> raw 20 -> net 0
    c = Contracts(100, 20, 0, 20, 10)
    items = _two(True, {"peak": 130, "sat_semi_peak": 160, "off_peak": 185}, c)
    assert items["sat_semi_peak"].excess_kw == 0
    # off raw 35 minus max(30, 20) = 5
    assert items["off_peak"].raw_excess_kw == pytest.approx(35)
    assert items["off_peak"].excess_kw == pytest.approx(5)


def test_three_stage_ignores_non_summer_contract():
    # Three-stage has no non-summer capacity (basic_charge ignores it too): a stray value
    # must not enter any threshold.
    c = Contracts(100, 20, 50, 20, 10)
    items = _by_period(over_contract("three_stage", False, {}, c,
                                     rates("high", "three_stage", False).basic))
    assert items["semi_peak"].cumulative_contract_kw == pytest.approx(150)
    assert items["sat_semi_peak"].cumulative_contract_kw == pytest.approx(170)
    assert items["off_peak"].cumulative_contract_kw == pytest.approx(180)
