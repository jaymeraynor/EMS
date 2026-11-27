"""SQLAlchemy 2.x models (PostgreSQL and SQLite). All datetimes are tz-aware UTC."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, MetaData,
    String, UniqueConstraint, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator):
    """timestamptz that always returns aware UTC datetimes (SQLite drops tzinfo)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime not allowed; use tz-aware values")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def _now() -> datetime:
    return datetime.now(timezone.utc)


BigId = BigInteger().with_variant(Integer, "sqlite")  # SQLite only autoincrements INTEGER PKs


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    organization: Mapped[Organization] = relationship()


class Meter(Base):
    __tablename__ = "meters"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    taipower_account_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 電號
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 hex
    api_key_prefix: Mapped[str] = mapped_column(String(16))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # tariff
    voltage: Mapped[str] = mapped_column(String(20), default="high")          # high | extra_high
    scheme: Mapped[str] = mapped_column(String(20), default="two_stage")      # two_stage | three_stage
    contract_regular_kw: Mapped[float] = mapped_column(Float(53), default=0.0)
    contract_non_summer_kw: Mapped[float] = mapped_column(Float(53), default=0.0)
    contract_semi_peak_kw: Mapped[float] = mapped_column(Float(53), default=0.0)
    contract_sat_semi_peak_kw: Mapped[float] = mapped_column(Float(53), default=0.0)
    contract_off_peak_kw: Mapped[float] = mapped_column(Float(53), default=0.0)
    customer_category: Mapped[str] = mapped_column(String(20), default="industrial")  # | residential
    # TODO: null until the customer's bill 行業別 is checked; treated as 1.0 with a warning
    industry_adjustment_coef: Mapped[Optional[float]] = mapped_column(Float(53), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    site: Mapped[Site] = relationship()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin','org_admin','viewer')", name="role_valid"),
        CheckConstraint("role = 'admin' OR org_id IS NOT NULL", name="org_required_unless_admin"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    org_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class Reading(Base):
    """Raw meter readings. Never auto-deleted: retain >= 1 year (see README)."""
    __tablename__ = "readings"
    __table_args__ = (
        UniqueConstraint("meter_id", "ts", name="uq_readings_meter_ts"),
        Index("ix_readings_meter_id_ts", "meter_id", "ts"),
        # neighbour lookups of the cumulative-register check (WHERE <col> IS NOT NULL)
        Index("ix_readings_meter_ts_kwh_notnull", "meter_id", "ts",
              postgresql_where=text("energy_kwh_total IS NOT NULL"),
              sqlite_where=text("energy_kwh_total IS NOT NULL")),
        Index("ix_readings_meter_ts_kvarh_notnull", "meter_id", "ts",
              postgresql_where=text("kvarh_total IS NOT NULL"),
              sqlite_where=text("kvarh_total IS NOT NULL")),
        CheckConstraint("source IN ('api','csv')", name="source_valid"),
    )
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))
    ts: Mapped[datetime] = mapped_column(UTCDateTime)
    power_kw: Mapped[float] = mapped_column(Float(53))
    energy_kwh_total: Mapped[Optional[float]] = mapped_column(Float(53), nullable=True)
    kvarh_total: Mapped[Optional[float]] = mapped_column(Float(53), nullable=True)
    source: Mapped[str] = mapped_column(String(10))
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class IngestBatch(Base):
    """Audit trail: one row per accepted ingest call / CSV import."""
    __tablename__ = "ingest_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"), index=True)
    source: Mapped[str] = mapped_column(String(10))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    received: Mapped[int] = mapped_column(Integer)
    inserted: Mapped[int] = mapped_column(Integer)
    duplicates: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
