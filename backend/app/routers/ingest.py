from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import AwareDatetime
from sqlalchemy import func, select

from app import models, schemas
from app.config import get_settings
from app.deps import DB, MeterOfKey, MeterOfUser, WritableMeter, WriterUser
from app.services.csv_import import CsvFormatError, CsvRowErrors, parse_csv
from app.services.ingest import IngestRejected, store_readings

router = APIRouter(tags=["ingest"])
MAX_PAGE = 10000


@router.post("/ingest", response_model=schemas.IngestResult)
def ingest(body: schemas.IngestBody, meter: MeterOfKey, db: DB):
    """Device endpoint: the X-API-Key identifies the meter; there is no meter_id in the body."""
    try:
        return store_readings(db, meter, body.readings, "api")
    except IngestRejected as exc:
        raise HTTPException(422,
                            [{"item": e["index"], "error": e["error"]} for e in exc.errors]) from None


@router.post("/meters/{meter_id}/readings/csv", response_model=schemas.IngestResult)
def import_csv(meter: WritableMeter, user: WriterUser, db: DB, file: Annotated[UploadFile, File()]):
    limit = get_settings().max_csv_bytes
    raw = file.file.read(limit + 1)   # sync route: runs in the threadpool, not the event loop
    if len(raw) > limit:
        raise HTTPException(413, f"檔案超過 {limit // 1024 // 1024} MB")
    try:
        items, rows = parse_csv(raw)
    except CsvFormatError as exc:
        raise HTTPException(422, str(exc)) from None
    except CsvRowErrors as exc:
        raise HTTPException(422, exc.errors) from None
    try:
        return store_readings(db, meter, items, "csv", user.id)
    except IngestRejected as exc:
        raise HTTPException(422,
                            [{"row": rows[e["index"]], "error": e["error"]} for e in exc.errors][:100]) from None


@router.get("/meters/{meter_id}/readings", response_model=schemas.ReadingPage)
def list_readings(meter: MeterOfUser, db: DB,
                  start: Optional[AwareDatetime] = None, end: Optional[AwareDatetime] = None,
                  limit: int = Query(default=1000, ge=1, le=MAX_PAGE), offset: int = Query(default=0, ge=0)):
    """Readings in [start, end), oldest first."""
    R = models.Reading
    cond = [R.meter_id == meter.id]
    if start is not None:
        cond.append(R.ts >= start)
    if end is not None:
        cond.append(R.ts < end)
    total = db.scalar(select(func.count()).select_from(R).where(*cond))
    items = db.scalars(select(R).where(*cond).order_by(R.ts).limit(limit).offset(offset)).all()
    return schemas.ReadingPage(total=total, limit=limit, offset=offset, items=items)
