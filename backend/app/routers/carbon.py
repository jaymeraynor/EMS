from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app import models
from app.config import get_settings
from app.deps import DB, CurrentUser, MeterOfUser, not_found
from app.services.carbon import CarbonError, factor_for, scope2_tco2e
from app.services.energy import integrate, year_window
from app.services.readings import load_samples

router = APIRouter(tags=["carbon"])
Year = Annotated[int, Query(ge=2000, le=2100)]


def _meter_scope2(db, meter: models.Meter, year: int) -> dict:
    try:
        factor = factor_for(year, meter.customer_category)
    except CarbonError as exc:
        raise HTTPException(422, str(exc)) from None
    start, end = year_window(year)
    res = integrate(load_samples(db, meter.id, start, end), start, end, get_settings().max_gap_minutes)
    return {
        "meter_id": meter.id, "name": meter.name, "is_demo": meter.is_demo, "year": year,
        "customer_category": meter.customer_category,
        "kwh": res.kwh, "coverage": res.coverage,
        "factor_kg_per_kwh": factor.kg_per_kwh, "factor_year": factor.factor_year,
        "provisional": factor.provisional, "factor_source": factor.source_url,
        "scope2_tco2e": scope2_tco2e(res.kwh, factor.kg_per_kwh),
        "warnings": factor.warnings,
    }


@router.get("/meters/{meter_id}/scope2")
def meter_scope2(meter: MeterOfUser, db: DB, year: Year):
    return _meter_scope2(db, meter, year)


@router.get("/orgs/{org_id}/scope2")
def org_scope2(org_id: int, db: DB, user: CurrentUser, year: Year):
    if user.role != "admin" and user.org_id != org_id:
        raise not_found("組織")
    if db.get(models.Organization, org_id) is None:
        raise not_found("組織")
    meters = db.scalars(select(models.Meter).join(models.Site).where(models.Site.org_id == org_id)
                        .order_by(models.Meter.id)).all()
    rows = [_meter_scope2(db, m, year) for m in meters]
    warnings = sorted({w for r in rows for w in r["warnings"]})
    return {
        "org_id": org_id, "year": year, "meters": rows,
        "kwh": sum(r["kwh"] for r in rows),
        # sum of per-meter rounded values would drift; round the exact sum once
        "scope2_tco2e": round(sum(r["scope2_tco2e"] for r in rows), 3),
        "provisional": any(r["provisional"] for r in rows),
        "warnings": warnings,
    }
