from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app import models, schemas, security
from app.deps import DB, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])

# verifying against this when the user is unknown keeps timing similar
_DUMMY_HASH = security.hash_password("dummy-password-for-timing")


@router.post("/login", response_model=schemas.Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    user = db.scalar(select(models.User).where(models.User.email == form.username.strip().lower()))
    ok = security.verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "帳號或密碼錯誤",
                            headers={"WWW-Authenticate": "Bearer"})
    return schemas.Token(access_token=security.create_access_token(user.id))


@router.get("/me", response_model=schemas.UserOut)
def me(user: CurrentUser):
    return user
