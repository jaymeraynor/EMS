"""Monthly Taipower bill for high / extra-high voltage (two-stage & three-stage fixed peak).

Rule sources: regs §2.3 rates, §2.4 basic charge, §2.5 over-contract, §2.6 power factor.
Billing period here is the Asia/Taipei calendar month.
TODO: real Taipower billing periods follow meter-reading dates, not calendar months.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Sequence

from app.services import tou
from app.services.energy import (
    DEFAULT_MAX_GAP_MINUTES, TAIPEI, Sample, blocks_between, month_window, register_total,
)
from app.services.tariff import BasicRates, TariffBook, load_default_book

SCHEMES = ("two_stage", "three_stage")
PERIODS = (tou.PEAK, tou.SEMI_PEAK, tou.SAT_SEMI_PEAK, tou.OFF_PEAK)
CROSS_SEASON_NOTE = "TODO: 台電跨季基本電費計算方式未核實，暫以日數比例"
ZERO_USAGE_FACTOR = 0.5   # regs §2.4
OVER_TIER_FRACTION = 0.10  # regs §2.5
OVER_TIER_MULTIPLIERS = (2, 3)


@dataclass(frozen=True)
class Contracts:
    regular: float = 0.0
    non_summer: float = 0.0
    semi_peak: float = 0.0
    sat_semi_peak: float = 0.0
    off_peak: float = 0.0

    @classmethod
    def from_meter(cls, m) -> "Contracts":
        return cls(m.contract_regular_kw or 0.0, m.contract_non_summer_kw or 0.0,
                   m.contract_semi_peak_kw or 0.0, m.contract_sat_semi_peak_kw or 0.0,
                   m.contract_off_peak_kw or 0.0)


def money(x: float) -> float:
    return float(Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# --- basic charge ---------------------------------------------------------------------

def basic_charge(scheme: str, summer: bool, c: Contracts, r: BasicRates) -> float:
    """Full-month basic charge (元) for one season's price list.

    two-stage : regular*C_reg [+ ns*C_ns in non-summer]
                + satoff * max(0, (C_sat + C_off) - (C_reg + C_ns) * 0.5)
    three-stage: regular*C_reg + semi*C_semi
                + satoff * max(0, (C_sat + C_off) - (C_reg + C_semi) * 0.5)
    """
    if scheme == "two_stage":
        total = r.regular * c.regular
        if not summer:
            total += (r.non_summer or 0.0) * c.non_summer
        half = (c.regular + c.non_summer) * 0.5
    elif scheme == "three_stage":
        total = r.regular * c.regular + (r.semi_peak or 0.0) * c.semi_peak
        half = (c.regular + c.semi_peak) * 0.5
    else:
        raise NotImplementedError(f"計費方式 {scheme!r} 尚未實作")
    return total + r.sat_off * max(0.0, (c.sat_semi_peak + c.off_peak) - half)


# --- over-contract -----------------------------------------------------------------------

@dataclass
class OverItem:
    period: str
    max_demand_kw: float
    cumulative_contract_kw: float
    raw_excess_kw: float
    excess_kw: float       # after non-duplication
    tier1_kw: float        # up to 10% of cumulative contract, billed 2x
    tier2_kw: float        # above 10%, billed 3x
    unit_price: float
    amount: float

    def as_dict(self) -> dict:
        return {k: (money(v) if k == "amount" else v) for k, v in self.__dict__.items()}


def over_contract(scheme: str, summer: bool, max_demand: dict[str, float], c: Contracts,
                  basic: BasicRates) -> list[OverItem]:
    """Excess demand surcharge (regs §2.5), per period.

    Cumulative contract per period (2-stage / 3-stage):
      peak = reg [+ ns outside summer] / reg ; semi_peak = reg + semi ;
      sat_semi_peak = previous + sat ; off_peak = previous + off.
      (The non-summer contract only exists outside summer, so it is not added in summer.)
    Non-duplication: net excess of a period = its raw excess minus the largest raw
    excess of any higher-priority period (peak, [semi_peak], sat_semi_peak), floored at 0.
    Billing: the part up to 10% of the cumulative contract x2, the rest x3.
    Unit price used (regs do not say explicitly -> ASSUMPTION flagged in the bill):
      peak -> regular price; semi_peak -> semi-peak contract price;
      sat_semi_peak and off_peak -> Saturday-semi-peak/off-peak contract price.
    Over-contract amounts get no power-factor discount (caller's responsibility).
    """
    if scheme == "two_stage":
        peak_cum = c.regular + (0.0 if summer else c.non_summer)
        plan = [(tou.PEAK, peak_cum, basic.regular),
                (tou.SAT_SEMI_PEAK, peak_cum + c.sat_semi_peak, basic.sat_off),
                (tou.OFF_PEAK, peak_cum + c.sat_semi_peak + c.off_peak, basic.sat_off)]
    elif scheme == "three_stage":
        semi_cum = c.regular + c.semi_peak
        plan = []
        if summer:
            plan.append((tou.PEAK, c.regular, basic.regular))
        plan += [(tou.SEMI_PEAK, semi_cum, basic.semi_peak or 0.0),
                 (tou.SAT_SEMI_PEAK, semi_cum + c.sat_semi_peak, basic.sat_off),
                 (tou.OFF_PEAK, semi_cum + c.sat_semi_peak + c.off_peak, basic.sat_off)]
    else:
        raise NotImplementedError(f"計費方式 {scheme!r} 尚未實作")
    items, prior_raw = [], []
    for period, cum, unit in plan:
        demand = max_demand.get(period, 0.0)
        raw = max(0.0, demand - cum)
        net = max(0.0, raw - max(prior_raw, default=0.0))
        prior_raw.append(raw)
        t1 = min(net, OVER_TIER_FRACTION * cum)
        t2 = net - t1
        amount = (OVER_TIER_MULTIPLIERS[0] * t1 + OVER_TIER_MULTIPLIERS[1] * t2) * unit
        items.append(OverItem(period, demand, cum, raw, net, t1, t2, unit, amount))
    return items


# --- power factor ----------------------------------------------------------------------------

@dataclass(frozen=True)
class PowerFactor:
    pf: float
    points: int      # whole percentage points (floor)
    rate: float      # +surcharge / -discount fraction of (basic+energy)


def power_factor_adjustment(kwh: float, kvarh: float) -> PowerFactor:
    """regs §2.6: below 80 -> +0.1% per point; above 80 -> -0.1% per point, credit capped at 95."""
    pf = kwh / math.hypot(kwh, kvarh) if kwh > 0 else 0.0
    points = int(math.floor(pf * 100 + 1e-9))
    if points < 80:
        rate = (80 - points) * 0.001
    elif points > 80:
        rate = -(min(points, 95) - 80) * 0.001
    else:
        rate = 0.0
    return PowerFactor(pf, points, rate)


# --- monthly bill ---------------------------------------------------------------------------------

def _parse_month(month) -> tuple[int, int]:
    if isinstance(month, str):
        y, m = month.split("-")
        return int(y), int(m)
    return month


def compute_bill(meter, samples: Sequence[Sample], month, *, book: Optional[TariffBook] = None,
                 offpeak_days: Optional[frozenset[date]] = None,
                 max_gap_minutes: float = DEFAULT_MAX_GAP_MINUTES) -> dict:
    scheme, voltage = meter.scheme, meter.voltage
    if scheme not in SCHEMES:
        raise NotImplementedError(f"計費方式 {scheme!r} 尚未實作（僅支援 two_stage / three_stage 固定尖峰）")
    book = book or load_default_book()
    offpeak = tou.load_offpeak_days() if offpeak_days is None else offpeak_days
    contracts = Contracts.from_meter(meter)
    year, mon = _parse_month(month)
    start, end = month_window(year, mon)
    assumptions = ["TODO: 台電實際計費期間依抄表日，此處以 Asia/Taipei 日曆月計算"]
    warnings: list[str] = []

    # segments = consecutive days sharing (tariff version, season)
    seg_days: "OrderedDict[tuple[str, bool], int]" = OrderedDict()
    day_seg: dict[date, tuple[str, bool]] = {}
    versions = {}
    d = date(year, mon, 1)
    while d < end.astimezone(TAIPEI).date():
        v = book.version_for(d)
        key = (v.version, tou.is_summer(d))
        versions[v.version] = v
        seg_days[key] = seg_days.get(key, 0) + 1
        day_seg[d] = key
        d += timedelta(days=1)
    n_days = len(day_seg)
    if len(seg_days) > 1:
        assumptions.append(CROSS_SEASON_NOTE)

    blocks = blocks_between(samples, start, end, max_gap_minutes)
    kwh_by_period = {p: 0.0 for p in PERIODS}
    seg_kwh = {k: {p: 0.0 for p in PERIODS} for k in seg_days}
    seg_demand = {k: {p: 0.0 for p in PERIODS} for k in seg_days}
    incomplete = 0
    for b in blocks:
        key = day_seg[b.start.date()]
        p = tou.classify(b.start, scheme, offpeak)
        kwh_by_period[p] += b.kwh
        seg_kwh[key][p] += b.kwh
        if b.complete:
            seg_demand[key][p] = max(seg_demand[key][p], b.demand_kw)
        else:
            incomplete += 1
    total_kwh = sum(kwh_by_period.values())
    max_demand = {p: max((seg_demand[k][p] for k in seg_days), default=0.0) for p in PERIODS}
    block_s = 15 * 60
    covered = sum(b.coverage for b in blocks) * block_s
    span = len(blocks) * block_s
    coverage = covered / span if span else 0.0

    # energy + basic + over-contract per segment
    energy = basic = 0.0
    over_items: list[dict] = []
    over_total = 0.0
    for (ver, summer), days in seg_days.items():
        rates = versions[ver].rates(voltage, scheme, summer)
        for p in PERIODS:
            if seg_kwh[(ver, summer)][p]:
                energy += seg_kwh[(ver, summer)][p] * rates.energy.for_period(p)
        basic += basic_charge(scheme, summer, contracts, rates.basic) * days / n_days
        for it in over_contract(scheme, summer, seg_demand[(ver, summer)], contracts, rates.basic):
            row = it.as_dict()
            row.update(season="summer" if summer else "non_summer", tariff_version=ver)
            over_items.append(row)
            over_total += it.amount

    zero_usage = total_kwh < 1e-9 and all(v < 1e-9 for v in max_demand.values()) and coverage > 0
    if zero_usage:
        basic *= ZERO_USAGE_FACTOR
        assumptions.append("當月未用電（度數與最高需量均為 0）：基本電費按 50% 計 (regs §2.4)")
    if coverage == 0:
        warnings.append("本月無資料覆蓋，未視為零用電；金額僅供參考")
    elif coverage < 1 - 1e-9:
        warnings.append(f"資料覆蓋率 {coverage:.1%}，缺資料時段未估算，電費可能偏低")
    if not offpeak:
        warnings.append("TODO: 離峰日日曆未核實（名單為空），國定假日暫以一般平日/週六計價")

    if over_total > 0:
        assumptions.append(
            "超約附加費單價假設：尖峰超約用經常契約單價、半尖峰超約用半尖峰契約單價、"
            "週六半尖峰與離峰超約用週六半尖峰/離峰契約單價（台電規定未明載）；"
            "夏月不計非夏月契約於累計契約容量")

    coef_raw = getattr(meter, "industry_adjustment_coef", None)
    coef_defaulted = coef_raw is None
    coef = 1.0 if coef_defaulted else float(coef_raw)
    if coef_defaulted:
        warnings.append("TODO: 行業別電價調整係數未設定，暫以 1.0 計算")

    basic_r, energy_r = money(basic), money(energy)
    base = money((basic_r + energy_r) * coef)

    # power factor
    has_kvarh = sum(1 for s in samples if s.kvarh_total is not None) >= 2
    pf_info: dict = {"available": False, "average_pf": None, "points": None, "rate": 0.0,
                     "kvarh": None, "amount": 0.0}
    if has_kvarh and total_kwh > 0:
        kvarh = register_total(samples, start, end, "kvarh_total", max_gap_minutes)
        pf = power_factor_adjustment(total_kwh, kvarh)
        pf_info.update(available=True, average_pf=round(pf.pf, 4), points=pf.points,
                       rate=pf.rate, kvarh=kvarh, amount=money(base * pf.rate))
        assumptions.append("功率因數以月平均 kWh/√(kWh²+kVARh²) 取整數百分點（無條件捨去）計算；"
                           "整數點數取法台電未明載")
    else:
        warnings.append("無 kVARh 讀數或無用電，未計功率因數調整")

    over_r = money(over_total)
    total = money(base + pf_info["amount"] + over_r)
    return {
        "month": f"{year:04d}-{mon:02d}",
        "tariff_version": next(iter(versions)),
        "tariff_versions": list(versions),
        "voltage": voltage,
        "scheme": scheme,
        "kwh_by_period": kwh_by_period,
        "total_kwh": total_kwh,
        "max_demand_kw_by_period": max_demand,
        "incomplete_blocks": incomplete,
        "basic_charge": basic_r,
        "energy_charge": energy_r,
        "coefficient": {"value": coef, "defaulted": coef_defaulted},
        "base_after_coefficient": base,
        "pf_adjustment": pf_info,
        "over_contract": {"amount": over_r, "items": over_items},
        "total": total,
        "currency": "TWD",
        "includes_vat": True,
        "vat_note": "電價含 5% 營業稅",
        "coverage": coverage,
        "gap_seconds": span - covered,
        "assumptions": assumptions,
        "warnings": warnings,
    }
