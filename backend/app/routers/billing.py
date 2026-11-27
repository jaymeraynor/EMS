from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.deps import DB, MeterOfUser
from app.services.billing import compute_bill
from app.services.energy import month_window
from app.services.readings import load_samples
from app.services.tariff import TariffError

router = APIRouter(tags=["billing"])


@router.get("/meters/{meter_id}/bill")
def bill(meter: MeterOfUser, db: DB,
         month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")]):
    year, mon = int(month[:4]), int(month[5:])
    try:
        start, end = month_window(year, mon)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    samples = load_samples(db, meter.id, start, end)
    try:
        result = compute_bill(meter, samples, month, max_gap_minutes=get_settings().max_gap_minutes)
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc)) from None
    except TariffError as exc:
        raise HTTPException(422, str(exc)) from None
    result["meter_id"] = meter.id
    result["is_demo"] = meter.is_demo
    return result
