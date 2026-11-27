from typing import Optional

from fastapi import APIRouter, Query

from sqlalchemy import select

from app import models, schemas, security
from app.deps import DB, CurrentUser, MeterOfUser, WritableMeter, WriterUser, get_site_for

router = APIRouter(tags=["meters"])


@router.post("/meters", response_model=schemas.MeterCreated, status_code=201)
def create_meter(body: schemas.MeterCreate, db: DB, user: WriterUser):
    get_site_for(db, user, body.site_id)
    key = security.generate_api_key()
    data = body.model_dump(exclude={"site_id"})
    meter = models.Meter(site_id=body.site_id, api_key_hash=security.hash_api_key(key),
                         api_key_prefix=key[:8], **data)
    db.add(meter)
    db.commit()
    # the plaintext key is returned here and nowhere else
    return schemas.MeterCreated(**schemas.MeterOut.model_validate(meter).model_dump(), api_key=key)


@router.get("/meters", response_model=list[schemas.MeterOut])
def list_meters(db: DB, user: CurrentUser, site_id: Optional[int] = Query(default=None)):
    q = select(models.Meter).join(models.Site).order_by(models.Meter.id)
    if user.role != "admin":
        q = q.where(models.Site.org_id == user.org_id)
    if site_id is not None:
        q = q.where(models.Meter.site_id == site_id)
    return db.scalars(q).all()


@router.get("/meters/{meter_id}", response_model=schemas.MeterOut)
def get_meter(meter: MeterOfUser):
    return meter


@router.patch("/meters/{meter_id}", response_model=schemas.MeterOut)
def update_meter(body: schemas.MeterUpdate, meter: WritableMeter, db: DB):
    for field in body.model_fields_set:
        value = getattr(body, field)
        if value is None and field != "industry_adjustment_coef" and field != "taipower_account_no":
            continue  # other columns are NOT NULL; ignore explicit nulls
        setattr(meter, field, value)
    db.commit()
    return meter


@router.post("/meters/{meter_id}/rotate-key")
def rotate_key(meter: WritableMeter, db: DB):
    key = security.generate_api_key()
    meter.api_key_hash = security.hash_api_key(key)
    meter.api_key_prefix = key[:8]
    db.commit()
    return {"id": meter.id, "api_key": key, "api_key_prefix": key[:8]}
