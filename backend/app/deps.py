"""Auth dependencies and org-scoped lookups.

Anything outside the caller's org answers 404 (not 403) so existence is not leaked.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, security
from app.db import get_db

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
DB = Annotated[Session, Depends(get_db)]


def _unauth() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "未登入或憑證無效",
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(db: DB, token: Annotated[str, Depends(oauth2)]) -> models.User:
    uid = security.decode_access_token(token)
    user = db.get(models.User, uid) if uid is not None else None
    if user is None or not user.is_active:
        raise _unauth()
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]


def require_roles(*roles: str):
    def dep(user: CurrentUser) -> models.User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "權限不足")
        return user
    return dep


AdminUser = Annotated[models.User, Depends(require_roles("admin"))]
WriterUser = Annotated[models.User, Depends(require_roles("admin", "org_admin"))]


def not_found(what: str = "資源") -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"找不到{what}")


def get_site_for(db: Session, user: models.User, site_id: int) -> models.Site:
    site = db.get(models.Site, site_id)
    if site is None or (user.role != "admin" and site.org_id != user.org_id):
        raise not_found("案場")
    return site


def get_meter_for(db: Session, user: models.User, meter_id: int) -> models.Meter:
    meter = db.get(models.Meter, meter_id)
    if meter is None or (user.role != "admin" and meter.site.org_id != user.org_id):
        raise not_found("電表")
    return meter


def org_id_of(meter: models.Meter) -> int:
    return meter.site.org_id


def visible_sites(db: Session, user: models.User):
    q = select(models.Site).order_by(models.Site.id)
    if user.role != "admin":
        q = q.where(models.Site.org_id == user.org_id)
    return db.scalars(q).all()


def meter_from_user(meter_id: int, db: DB, user: CurrentUser) -> models.Meter:
    return get_meter_for(db, user, meter_id)


def writable_meter(meter_id: int, db: DB, user: WriterUser) -> models.Meter:
    return get_meter_for(db, user, meter_id)


MeterOfUser = Annotated[models.Meter, Depends(meter_from_user)]
WritableMeter = Annotated[models.Meter, Depends(writable_meter)]


def meter_from_api_key(db: DB, x_api_key: Annotated[str | None, Header()] = None) -> models.Meter:
    if not x_api_key:
        raise _unauth()
    meter = db.scalar(select(models.Meter).where(
        models.Meter.api_key_hash == security.hash_api_key(x_api_key)))
    if meter is None:
        raise _unauth()
    return meter


MeterOfKey = Annotated[models.Meter, Depends(meter_from_api_key)]
