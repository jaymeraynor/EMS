"""Versioned Taipower tariff tables loaded from YAML (validated with pydantic)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

TARIFF_DIR = Path(__file__).resolve().parent.parent / "data" / "tariffs"


class TariffError(ValueError):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BasicRates(_Strict):
    regular: float
    non_summer: Optional[float] = None   # two-stage only
    semi_peak: Optional[float] = None    # three-stage only
    sat_off: float                       # Saturday-semi-peak / off-peak contract


class EnergyRates(_Strict):
    peak: Optional[float] = None
    semi_peak: Optional[float] = None
    sat_semi_peak: float
    off_peak: float

    def for_period(self, period: str) -> float:
        v = getattr(self, period)
        if v is None:
            raise TariffError(f"此費率無 {period} 時段單價")
        return v


class SeasonRates(_Strict):
    basic: BasicRates
    energy: EnergyRates


class SchemeRates(_Strict):
    summer: SeasonRates
    non_summer: SeasonRates


class VoltageRates(_Strict):
    two_stage: SchemeRates
    three_stage: SchemeRates


class TariffVersion(_Strict):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: str
    effective_from: date
    effective_to: Optional[date] = None   # inclusive last day; None = open-ended
    source_url: str
    verified_on: date
    includes_vat: bool
    tables: dict[str, VoltageRates] = Field(alias="rates")

    def rates(self, voltage: str, scheme: str, summer: bool) -> SeasonRates:
        try:
            sch = getattr(self.tables[voltage], scheme)
        except (KeyError, AttributeError):
            raise TariffError(f"無此電價組合: {voltage}/{scheme}") from None
        return sch.summer if summer else sch.non_summer

    def covers(self, d: date) -> bool:
        return d >= self.effective_from and (self.effective_to is None or d <= self.effective_to)


class TariffBook:
    def __init__(self, versions: list[TariffVersion]):
        ordered = sorted(versions, key=lambda v: v.effective_from)
        for a, b in zip(ordered, ordered[1:]):
            if a.effective_to is None or a.effective_to >= b.effective_from:
                raise TariffError(f"電價版本期間重疊: {a.version} / {b.version}")
        self.versions = ordered

    def version_for(self, d: date) -> TariffVersion:
        for v in self.versions:
            if v.covers(d):
                return v
        raise TariffError(f"{d} 無適用的電價版本")


def load_tariff_file(path: Path) -> TariffVersion:
    try:
        return TariffVersion.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
    except (ValidationError, yaml.YAMLError, TypeError) as exc:
        raise TariffError(f"電價檔格式錯誤 {path}: {exc}") from exc


def load_default_book() -> TariffBook:
    files = sorted(TARIFF_DIR.glob("*.yaml"))
    if not files:
        raise TariffError("找不到電價檔")
    return TariffBook([load_tariff_file(f) for f in files])
