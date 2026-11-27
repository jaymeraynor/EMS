from fastapi import APIRouter

from app import models, schemas
from app.deps import DB, CurrentUser, WriterUser, get_site_for, not_found, visible_sites

router = APIRouter(tags=["sites"])


@router.post("/sites", response_model=schemas.SiteOut, status_code=201)
def create_site(body: schemas.SiteCreate, db: DB, user: WriterUser):
    if user.role == "org_admin":
        if body.org_id is not None and body.org_id != user.org_id:
            raise not_found("組織")
        org_id = user.org_id
    else:
        if body.org_id is None or db.get(models.Organization, body.org_id) is None:
            raise not_found("組織")
        org_id = body.org_id
    site = models.Site(org_id=org_id, name=body.name.strip(), address=body.address)
    db.add(site)
    db.commit()
    return site


@router.get("/sites", response_model=list[schemas.SiteOut])
def list_sites(db: DB, user: CurrentUser):
    return visible_sites(db, user)


@router.get("/sites/{site_id}", response_model=schemas.SiteOut)
def get_site(site_id: int, db: DB, user: CurrentUser):
    return get_site_for(db, user, site_id)
