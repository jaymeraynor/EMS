from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, field_validator,
)

from app.config import get_settings

Role = Literal["admin", "org_admin", "viewer"]
Voltage = Literal["high", "extra_high"]
Scheme = Literal["two_stage", "three_stage"]
Category = Literal["industrial", "residential"]
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+$")

NonNegFloat = Field(ge=0, allow_inf_nan=False)


def _norm_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL.match(v) or len(v) > 320:
        raise ValueError("invalid email")
    return v


def _check_password(v: str) -> str:
    if len(v) < 10:
        raise ValueError("password must be at least 10 characters")
    if len(v.encode()) > 72:
        raise ValueError("password must be at most 72 bytes")
    return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: Role
    org_id: Optional[int]
    is_active: bool


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str
    role: Role
    org_id: Optional[int] = None

    _email = field_validator("email")(_norm_email)
    _pw = field_validator("password")(_check_password)


class OrgCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class SiteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    org_id: Optional[int] = None  # admin only; org_admin is always bound to own org


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    org_id: int
    name: str
    address: Optional[str]


class _MeterTariff(BaseModel):
    voltage: Voltage = "high"
    scheme: Scheme = "two_stage"
    contract_regular_kw: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    contract_non_summer_kw: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    contract_semi_peak_kw: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    contract_sat_semi_peak_kw: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    contract_off_peak_kw: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    customer_category: Category = "industrial"
    # TODO: null -> billed as 1.0 with a warning until the customer's 行業別 coefficient is known
    industry_adjustment_coef: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)


class MeterCreate(_MeterTariff):
    model_config = ConfigDict(extra="forbid")
    site_id: int
    name: str = Field(min_length=1, max_length=200)
    taipower_account_no: Optional[str] = Field(default=None, max_length=20)
    is_demo: bool = False


class MeterUpdate(BaseModel):
    """PATCH body: only fields present are changed (so coefficient can be reset to null)."""
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    taipower_account_no: Optional[str] = Field(default=None, max_length=20)
    is_demo: Optional[bool] = None
    voltage: Optional[Voltage] = None
    scheme: Optional[Scheme] = None
    contract_regular_kw: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    contract_non_summer_kw: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    contract_semi_peak_kw: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    contract_sat_semi_peak_kw: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    contract_off_peak_kw: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    customer_category: Optional[Category] = None
    industry_adjustment_coef: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)


class MeterOut(_MeterTariff):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    name: str
    taipower_account_no: Optional[str]
    is_demo: bool
    api_key_prefix: str


class MeterCreated(MeterOut):
    api_key: str  # shown exactly once


class ReadingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ts: AwareDatetime
    power_kw: float = Field(ge=0, allow_inf_nan=False)
    energy_kwh_total: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    kvarh_total: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)

    @field_validator("ts")
    @classmethod
    def _not_in_future(cls, v: datetime) -> datetime:
        limit = datetime.now(timezone.utc) + timedelta(seconds=get_settings().ingest_max_future_skew_s)
        if v > limit:
            raise ValueError("timestamp is in the future")
        return v


class IngestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    readings: list[ReadingIn] = Field(min_length=1, max_length=5000)


class IngestResult(BaseModel):
    received: int
    inserted: int
    duplicates: int


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts: datetime
    power_kw: float
    energy_kwh_total: Optional[float]
    kvarh_total: Optional[float]
    source: str


class ReadingPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ReadingOut]
