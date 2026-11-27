"""Bill tests. Every expected number is hand-computed from the regs tables
(regs §2.3 rates, §2.4 basic, §2.5 over-contract, §2.6 power factor); see comments."""
from datetime import date
from types import SimpleNamespace

import pytest

from app.services.billing import (
    Contracts, basic_charge, compute_bill, over_contract, power_factor_adjustment,
)
from app.services.energy import month_window
from app.services.tariff import load_default_book
from tests.helpers import grid

CROSS_SEASON_NOTE = "TODO: 台電跨季基本電費計算方式未核實，暫以日數比例"


def meter(voltage="high", scheme="two_stage", reg=100.0, ns=0.0, semi=0.0, sat=40.0, off=40.0,
          coef=None):
    return SimpleNamespace(
        voltage=voltage, scheme=scheme, contract_regular_kw=reg, contract_non_summer_kw=ns,
        contract_semi_peak_kw=semi, contract_sat_semi_peak_kw=sat, contract_off_peak_kw=off,
        industry_adjustment_coef=coef)


def month_samples(year, month, power_kw=100.0, **kw):
    start, end = month_window(year, month)
    return grid(start, end, 15, power_kw, **kw)


# --- basic charge (regs 2.4) ----------------------------------------------------

BOOK = load_default_book()


def rates(voltage, scheme, summer):
    return BOOK.version_for(date(2026, 7, 1 if summer else 1)).rates(voltage, scheme, summer)


def test_basic_two_stage_summer():
    # 223.60*100 + 44.70*max(0,(40+40) - (100+0)*0.5 = 30) = 22,360 + 1,341 = 23,701.00
    c = Contracts(regular=100, non_summer=0, semi_peak=0, sat_semi_peak=40, off_peak=40)
    assert basic_charge("two_stage", True, c, rates("high", "two_stage", True).basic) \
        == pytest.approx(23701.00)


def test_basic_two_stage_summer_deduction_floored_at_zero():
    # (10+10) - 100*0.5 = -30 -> 0 ; 223.60*100 = 22,360
    c = Contracts(100, 0, 0, 10, 10)
    assert basic_charge("two_stage", True, c, rates("high", "two_stage", True).basic) \
        == pytest.approx(22360.00)


def test_basic_two_stage_non_summer():
    # 166.90*100 + 166.90*20 + 33.30*max(0,(30+50) - (100+20)*0.5=60 -> 20)
    # = 16,690 + 3,338 + 666 = 20,694.00
    c = Contracts(100, 20, 0, 30, 50)
    assert basic_charge("two_stage", False, c, rates("high", "two_stage", False).basic) \
        == pytest.approx(20694.00)


def test_basic_three_stage_summer():
    # 223.60*100 + 166.90*50 + 44.70*max(0,(60+40) - (100+50)*0.5=75 -> 25)
    # = 22,360 + 8,345 + 1,117.50 = 31,822.50
    c = Contracts(100, 0, 50, 60, 40)
    assert basic_charge("three_stage", True, c, rates("high", "three_stage", True).basic) \
        == pytest.approx(31822.50)


# --- over contract (regs 2.5) -------------------------------------------------------

def _by_period(items):
    return {i.period: i for i in items}


def test_over_contract_two_stage_summer_non_duplication_and_tiers():
    # contracts: reg 100, sat 20, off 10 ; max demand: peak 130, sat 160, off 180
    # peak excess = 130-100 = 30 ; cum 100 -> 10% = 10 kW
    #   tier1 10*2*223.60 = 4,472.00 ; tier2 20*3*223.60 = 13,416.00 ; total 17,888.00
    # sat raw = 160-(100+20) = 40 ; net = 40-30 = 10 ; cum 120 -> 10% = 12 -> all tier1
    #   10*2*44.70 = 894.00
    # off raw = 180-(100+20+10) = 50 ; net = 50 - max(30,40) = 10 ; cum 130 -> tier1
    #   10*2*44.70 = 894.00
    c = Contracts(100, 0, 0, 20, 10)
    items = _by_period(over_contract(
        "two_stage", True, {"peak": 130, "sat_semi_peak": 160, "off_peak": 180}, c,
        rates("high", "two_stage", True).basic))
    assert items["peak"].excess_kw == pytest.approx(30)
    assert (items["peak"].tier1_kw, items["peak"].tier2_kw) == (pytest.approx(10), pytest.approx(20))
    assert items["peak"].amount == pytest.approx(17888.00)
    assert items["sat_semi_peak"].excess_kw == pytest.approx(10)
    assert items["sat_semi_peak"].amount == pytest.approx(894.00)
    assert items["off_peak"].excess_kw == pytest.approx(10)
    assert items["off_peak"].amount == pytest.approx(894.00)


def test_over_contract_none_when_demand_within_contract():
    c = Contracts(100, 0, 0, 20, 10)
    items = over_contract("two_stage", True, {"peak": 100, "sat_semi_peak": 100, "off_peak": 100},
                          c, rates("high", "two_stage", True).basic)
    assert sum(i.amount for i in items) == 0


def test_over_contract_two_stage_non_summer_cumulative_includes_non_summer_contract():
    # reg 100, ns 20 -> peak cumulative 120 ; peak demand 130 -> excess 10 (<= 12)
    # 10*2*166.90 = 3,338.00
    c = Contracts(100, 20, 0, 10, 10)
    items = _by_period(over_contract("two_stage", False, {"peak": 130}, c,
                                     rates("high", "two_stage", False).basic))
    assert items["peak"].cumulative_contract_kw == pytest.approx(120)
    assert items["peak"].amount == pytest.approx(3338.00)


def test_over_contract_three_stage_summer():
    # reg 100, semi 50, sat 20, off 10 ; demand peak 120, semi 190, sat 200, off 100
    # peak: 120-100 = 20 ; cum 100, 10% = 10 -> 10*2*223.60 + 10*3*223.60
    #       = 4,472.00 + 6,708.00 = 11,180.00
    # semi: raw 190-(100+50) = 40 ; net 40-20 = 20 ; cum 150, 10% = 15
    #       -> 15*2*166.90 + 5*3*166.90 = 5,007.00 + 2,503.50 = 7,510.50
    # sat : raw 200-(150+20) = 30 ; minus max(peak raw 20, semi raw 40) -> 0
    # off : raw 100-(170+10) < 0 -> 0
    c = Contracts(100, 0, 50, 20, 10)
    items = _by_period(over_contract(
        "three_stage", True,
        {"peak": 120, "semi_peak": 190, "sat_semi_peak": 200, "off_peak": 100}, c,
        rates("high", "three_stage", True).basic))
    assert items["peak"].amount == pytest.approx(11180.00)
    assert items["semi_peak"].amount == pytest.approx(7510.50)
    assert items["sat_semi_peak"].amount == 0
    assert items["off_peak"].amount == 0


# --- power factor (regs 2.6) -------------------------------------------------------------

@pytest.mark.parametrize("kwh,kvarh,pf_pct,rate", [
    (900, 1200, 60, 0.02),     # pf .6  -> 20 points below 80 -> +2.0 %
    (1000, 750, 80, 0.0),      # pf .8  -> exactly 80 -> no adjustment
    (1500, 800, 88, -0.008),   # 1500/1700=.8823 -> 88 -> 8 pts above 80 -> -0.8 %
    (1200, 500, 92, -0.012),   # 1200/1300=.9230 -> 92 -> -1.2 %
    (960, 280, 96, -0.015),    # .96 -> 96 -> only up to 95 counts -> -1.5 % max
])
def test_power_factor_adjustment(kwh, kvarh, pf_pct, rate):
    r = power_factor_adjustment(kwh, kvarh)
    assert r.points == pf_pct
    assert r.rate == pytest.approx(rate)


# --- monthly bill --------------------------------------------------------------------------

def test_bill_two_stage_summer_flat_100kw_july():
    # July 2026: 23 weekdays, 4 Sat, 4 Sun; flat 100 kW.
    # peak 09-24 weekdays: 23*15*100 = 34,500 kWh ; sat 09-24: 4*15*100 = 6,000
    # off: weekdays 0-9 23*9*100=20,700 + Sat 0-9 3,600 + Sun 9,600 = 33,900 kWh
    # energy = 34,500*6.75 + 6,000*2.77 + 33,900*2.71
    #        = 232,875 + 16,620 + 91,869 = 341,364.00
    # basic (reg 100, sat 40, off 40) = 23,701.00 (see basic test)
    # max demand 100 in every period -> no excess ; no kvarh -> no pf adj ; coef None -> 1.0
    # total = 23,701 + 341,364 = 365,065.00
    b = compute_bill(meter(), month_samples(2026, 7), "2026-07")
    assert b["tariff_version"] == "taipower-2025-10-01"
    assert b["kwh_by_period"]["peak"] == pytest.approx(34500)
    assert b["kwh_by_period"]["sat_semi_peak"] == pytest.approx(6000)
    assert b["kwh_by_period"]["off_peak"] == pytest.approx(33900)
    assert b["max_demand_kw_by_period"]["peak"] == pytest.approx(100)
    assert b["basic_charge"] == pytest.approx(23701.00)
    assert b["energy_charge"] == pytest.approx(341364.00)
    assert b["over_contract"]["amount"] == 0
    assert b["pf_adjustment"]["amount"] == 0
    assert b["total"] == pytest.approx(365065.00)
    assert b["coverage"] == pytest.approx(1.0)
    assert b["incomplete_blocks"] == 0
    assert b["coefficient"] == {"value": 1.0, "defaulted": True}
    assert any("TODO" in w and "行業" in w for w in b["warnings"])   # coef default warning
    assert any("離峰日" in w for w in b["warnings"])                  # empty calendar warning
    assert any("kVARh" in w or "kvarh" in w for w in b["warnings"])   # no pf data
    assert CROSS_SEASON_NOTE not in b["assumptions"]


def test_bill_rounds_to_two_decimals_and_states_vat():
    b = compute_bill(meter(), month_samples(2026, 7), "2026-07")
    assert b["currency"] == "TWD" and b["includes_vat"] is True
    assert round(b["total"], 2) == b["total"]


def test_bill_industry_coefficient_applied_to_basic_plus_energy():
    # (23,701 + 341,364) * 0.9 = 328,558.50
    b = compute_bill(meter(coef=0.9), month_samples(2026, 7), "2026-07")
    assert b["coefficient"] == {"value": 0.9, "defaulted": False}
    assert b["total"] == pytest.approx(328558.50)
    assert not any("行業" in w for w in b["warnings"])


def test_bill_with_over_contract_has_no_pf_discount_on_it():
    # reg 100 -> 80, sat 0, off 0. basic = 223.60*80 + 44.70*max(0, 0-40) = 17,888.00
    # peak excess 100-80 = 20 : cum 80, 10% = 8 -> 8*2*223.60 = 3,577.60 ; 12*3*223.60 = 8,049.60
    #   = 11,627.20 ; sat raw 20 - 20 = 0 ; off raw 20 - max(20,20) = 0
    # energy 341,364.00 ; total = 17,888 + 341,364 + 11,627.20 = 370,879.20
    b = compute_bill(meter(reg=80, sat=0, off=0), month_samples(2026, 7), "2026-07")
    assert b["basic_charge"] == pytest.approx(17888.00)
    assert b["over_contract"]["amount"] == pytest.approx(11627.20)
    assert b["total"] == pytest.approx(370879.20)
    assert any("單價" in a for a in b["assumptions"])  # unit price choice flagged


def test_bill_power_factor_surcharge_applied_to_basic_plus_energy_only():
    # kvarh = 4/3 of kWh -> pf = 3/5 = 0.60 -> 60 pts -> 20 below 80 -> +2.0 %
    # (23,701 + 341,364) * 0.02 = 7,301.30 ; total = 365,065 + 7,301.30 = 372,366.30
    b = compute_bill(meter(), month_samples(2026, 7, with_registers=True, kvarh_ratio=4 / 3),
                     "2026-07")
    assert b["pf_adjustment"]["points"] == 60
    assert b["pf_adjustment"]["amount"] == pytest.approx(7301.30)
    assert b["total"] == pytest.approx(372366.30)
    assert any("整數" in a or "百分" in a for a in b["assumptions"])  # whole-point assumption


def test_bill_three_stage_summer():
    # weekdays(23): peak 16-22 = 6h -> 13,800 ; semi 09-16 + 22-24 = 9h -> 20,700 ; off 0-9 -> 20,700
    # Sat(4): 09-24 sat_semi 6,000 ; 0-9 off 3,600 ; Sun 9,600 -> off total 33,900
    # energy = 13,800*9.39 + 20,700*5.85 + 6,000*2.60 + 33,900*2.53
    #        = 129,582 + 121,095 + 15,600 + 85,767 = 352,044.00
    # basic (reg 100, semi 50, sat 20, off 10) = 22,360 + 166.90*50 (8,345) + 44.70*max(0,30-75)=0
    #        = 30,705.00 ; total = 382,749.00
    m = meter(scheme="three_stage", reg=100, semi=50, sat=20, off=10)
    b = compute_bill(m, month_samples(2026, 7), "2026-07")
    assert b["kwh_by_period"]["peak"] == pytest.approx(13800)
    assert b["kwh_by_period"]["semi_peak"] == pytest.approx(20700)
    assert b["energy_charge"] == pytest.approx(352044.00)
    assert b["basic_charge"] == pytest.approx(30705.00)
    assert b["total"] == pytest.approx(382749.00)


def test_bill_extra_high_non_summer_february():
    # Feb 2026: 20 weekdays, 4 Sat, 4 Sun ; 100 kW flat ; extra-high two-stage non-summer
    # peak (06-11, 14-24 = 15h) 20*15*100 = 30,000 ; sat_semi 4*15*100 = 6,000
    # off: weekdays 9h 18,000 + Sat 3,600 + Sun 9,600 = 31,200
    # energy = 30,000*5.79 + 6,000*2.48 + 31,200*2.28 = 173,700 + 14,880 + 71,136 = 259,716.00
    # basic (reg 100, ns 20, sat 10, off 10) = 160.60*100 + 160.60*20 + 32.10*max(0,20-60) = 19,272.00
    # total 278,988.00
    m = meter(voltage="extra_high", reg=100, ns=20, sat=10, off=10)
    b = compute_bill(m, month_samples(2026, 2), "2026-02")
    assert b["energy_charge"] == pytest.approx(259716.00)
    assert b["basic_charge"] == pytest.approx(19272.00)
    assert b["total"] == pytest.approx(278988.00)


def test_bill_zero_usage_month_basic_charge_is_half():
    # no usage and no demand: basic 23,701 * 50% = 11,850.50 ; energy 0
    b = compute_bill(meter(), month_samples(2026, 7, power_kw=0.0, with_registers=True), "2026-07")
    assert b["energy_charge"] == 0
    assert b["basic_charge"] == pytest.approx(11850.50)
    assert b["total"] == pytest.approx(11850.50)


def test_bill_without_any_data_is_not_treated_as_zero_usage():
    b = compute_bill(meter(), [], "2026-07")
    assert b["coverage"] == 0
    assert b["basic_charge"] == pytest.approx(23701.00)
    assert any("無資料" in w or "覆蓋" in w for w in b["warnings"])


def test_bill_cross_season_month_prorates_basic_by_days_and_flags_assumption():
    # May 2026: 1-15 non-summer (15 d), 16-31 summer (16 d). reg 100, ns 20, sat 10, off 10
    # non-summer basic = 16,690 + 3,338 + 33.30*max(0,20-60) = 20,028.00
    # summer basic     = 22,360 + 44.70*max(0, 20-60) = 22,360.00
    # prorated = (20,028*15 + 22,360*16)/31 = 658,180/31 = 21,231.61
    # flat 10 kW. non-summer May1-15: 11 weekdays, 2 Sat, 2 Sun ->
    #   peak 11*15*10=1,650 ; sat 2*15*10=300 ; off 990+180+480 = 1,650
    #   energy = 1,650*6.37 + 300*2.54 + 1,650*2.46 = 10,510.5 + 762 + 4,059 = 15,331.50
    # summer May16-31: 10 weekdays, 3 Sat, 3 Sun ->
    #   peak 10*15*10=1,500 ; sat 3*15*10=450 ; off 900+270+720 = 1,890
    #   energy = 1,500*6.75 + 450*2.77 + 1,890*2.71 = 10,125 + 1,246.5 + 5,121.9 = 16,493.40
    # energy 31,824.90 ; total = 21,231.61 + 31,824.90 = 53,056.51
    m = meter(reg=100, ns=20, sat=10, off=10)
    b = compute_bill(m, month_samples(2026, 5, power_kw=10.0), "2026-05")
    assert CROSS_SEASON_NOTE in b["assumptions"]
    assert b["basic_charge"] == pytest.approx(21231.61)
    assert b["energy_charge"] == pytest.approx(31824.90)
    assert b["total"] == pytest.approx(53056.51)
    assert b["kwh_by_period"]["peak"] == pytest.approx(3150)


def test_bill_splits_energy_by_day_when_tariff_version_changes_mid_month():
    # v2 from 2026-07-16 with energy rates x2 (basic same). 100 kW flat July.
    # Jul 1-15 (11 weekdays, 2 Sat, 2 Sun): peak 16,500 ; sat 3,000 ; off 16,500
    #   = 16,500*6.75 + 3,000*2.77 + 16,500*2.71 = 111,375 + 8,310 + 44,715 = 164,400
    # Jul 16-31 (12 weekdays, 2 Sat, 2 Sun): peak 18,000 ; sat 3,000 ; off 17,400
    #   v1 price would be 121,500 + 8,310 + 47,154 = 176,964 -> v2 (x2) = 353,928
    # energy = 164,400 + 353,928 = 518,328.00 ; basic 23,701 (same price both halves)
    # total = 542,029.00
    v1 = BOOK.version_for(date(2026, 7, 1)).model_copy(update={"effective_to": date(2026, 7, 15)})
    v2 = v1.model_copy(deep=True, update={"version": "v2", "effective_from": date(2026, 7, 16),
                                          "effective_to": None})
    for volt in v2.tables.values():
        for scheme in (volt.two_stage, volt.three_stage):
            for season in (scheme.summer, scheme.non_summer):
                e = season.energy
                for f in ("peak", "semi_peak", "sat_semi_peak", "off_peak"):
                    if getattr(e, f) is not None:
                        setattr(e, f, getattr(e, f) * 2)
    from app.services.tariff import TariffBook
    b = compute_bill(meter(), month_samples(2026, 7), "2026-07", book=TariffBook([v1, v2]))
    assert b["energy_charge"] == pytest.approx(518328.00)
    assert b["basic_charge"] == pytest.approx(23701.00)
    assert b["total"] == pytest.approx(542029.00)
    assert b["tariff_versions"] == ["taipower-2025-10-01", "v2"]


def test_incomplete_blocks_are_counted_and_energy_still_billed():
    # Drop the readings strictly between 12:00 and 13:00 Taipei on 2026-07-01 (04:00Z-05:00Z):
    # the 60-min segment is not integrated, so 4 blocks (12:00-13:00) are incomplete.
    # They add no kWh (peak 34,500 - 100 kW*1 h = 34,400) and no max-demand candidate.
    from tests.helpers import utc
    lo, hi = utc("2026-07-01T04:00"), utc("2026-07-01T05:00")
    samples = [s for s in month_samples(2026, 7) if not (lo < s.ts < hi)]
    b = compute_bill(meter(), samples, "2026-07")
    assert b["incomplete_blocks"] == 4
    assert b["kwh_by_period"]["peak"] == pytest.approx(34400)
    assert b["max_demand_kw_by_period"]["peak"] == pytest.approx(100)
    assert b["coverage"] == pytest.approx(1 - 4 / 2976)
    assert any("覆蓋率" in w for w in b["warnings"])
