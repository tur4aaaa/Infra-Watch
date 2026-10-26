import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from pydantic import BaseModel, EmailStr, Field

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.postgres import User, get_session
from database.redis_client import get_redis_client

router = APIRouter(prefix="/auth", tags=["auth"])

hasher = PasswordHasher()
session_cookie = "session"
session_TTL = 7 * 24 * 3600  # 7 days in seconds

# its a not valid hash in order to check it if there is no user(no time attacks)
not_valid_hash = hasher.hash("not_valid_hash for timing")


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


# Who creates a request
def get_current_user(request: Request, db: Session = Depends(get_session)) -> User:
    session_id = request.cookies.get(session_cookie)
    user_id = get_redis_client().get(session_key(session_id)) if session_id else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ENDPOINTS

@router.post("/register", status_code=201)
def register(data: Credentials, db: Session = Depends(get_session)):
    email = data.email.lower()

    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=email, password_hash=hasher.hash(data.password))
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email}


@router.post("/login")
def login(data: Credentials, response: Response, db: Session = Depends(get_session)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))

    try:
        hasher.verify(user.password_hash if user else not_valid_hash, data.password)
    except VerifyMismatchError:
        user = None

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_id = secrets.token_urlsafe(32)
    get_redis_client().set(session_key(session_id), user.id, ex=session_TTL)

    response.set_cookie(
        session_cookie,
        session_id,
        max_age=session_TTL,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return {"email": user.email}


@router.post("/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get(session_cookie)
    if session_id:
        get_redis_client().delete(session_key(session_id))
    response.delete_cookie(session_cookie)
    return {"status": "ok"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}