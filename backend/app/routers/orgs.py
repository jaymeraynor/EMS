from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import models, schemas, security
from app.deps import DB, AdminUser, CurrentUser, WriterUser, not_found

router = APIRouter(tags=["orgs"])


@router.post("/orgs", response_model=schemas.OrgOut, status_code=201)
def create_org(body: schemas.OrgCreate, db: DB, _: AdminUser):
    org = models.Organization(name=body.name.strip())
    db.add(org)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "組織名稱已存在") from None
    return org


@router.get("/orgs", response_model=list[schemas.OrgOut])
def list_orgs(db: DB, user: CurrentUser):
    q = select(models.Organization).order_by(models.Organization.id)
    if user.role != "admin":
        q = q.where(models.Organization.id == user.org_id)
    return db.scalars(q).all()


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(body: schemas.UserCreate, db: DB, actor: WriterUser):
    if actor.role == "org_admin":
        if body.role == "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "權限不足：不可建立系統管理員")
        if body.org_id is not None and body.org_id != actor.org_id:
            raise not_found("組織")
        org_id: Optional[int] = actor.org_id
    else:
        if body.role == "admin":
            org_id = None
        else:
            if body.org_id is None:
                raise HTTPException(422, "非管理員角色必須指定 org_id")
            if db.get(models.Organization, body.org_id) is None:
                raise not_found("組織")
            org_id = body.org_id
    user = models.User(email=body.email, password_hash=security.hash_password(body.password),
                       role=body.role, org_id=org_id, is_active=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "此 Email 已被使用") from None
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: DB, actor: WriterUser):
    q = select(models.User).order_by(models.User.id)
    if actor.role != "admin":
        q = q.where(models.User.org_id == actor.org_id)
    return db.scalars(q).all()
