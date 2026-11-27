"""Scope 2 (purchased electricity) emissions. Factors: data/emission_factors.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

import yaml

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "emission_factors.yaml"
CATEGORIES = ("public", "industrial", "residential")


class CarbonError(ValueError):
    pass


@dataclass
class Factor:
    kg_per_kwh: float
    factor_year: int
    requested_year: int
    category: str
    provisional: bool
    source_url: str
    warnings: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _load() -> dict:
    return yaml.safe_load(DATA_FILE.read_text(encoding="utf-8"))


def factor_for(year: int, category: str) -> Factor:
    data = _load()
    if category not in CATEGORIES:
        raise CarbonError(f"未知的用戶類別: {category!r}")
    by_year = {int(f["year"]): f for f in data["factors"]}
    latest = max(by_year)
    if year in by_year:
        return Factor(by_year[year][category], year, year, category, False, data["source_url"])
    if year > latest:
        return Factor(
            by_year[latest][category], latest, year, category, True, data["source_url"],
            [f"{year} 年度排碳係數尚未公布，暫用 {latest} 年度係數（provisional）"])
    raise CarbonError(f"{year} 年度排碳係數未收錄，不以較新年度係數回推")


def _exact_tco2e(kwh: float, kg_per_kwh: float) -> Decimal:
    return Decimal(str(kwh)) * Decimal(str(kg_per_kwh)) / Decimal(1000)


def _round3(v: Decimal) -> float:
    return float(v.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def scope2_tco2e(kwh: float, kg_per_kwh: float) -> float:
    """tCO2e = kWh * factor / 1000, half-up to 3 decimals."""
    return _round3(_exact_tco2e(kwh, kg_per_kwh))


def sum_scope2_tco2e(parts) -> float:
    """Organisation total from (kwh, kg_per_kwh) pairs: sum unrounded, round half-up once."""
    return _round3(sum((_exact_tco2e(k, f) for k, f in parts), Decimal(0)))
