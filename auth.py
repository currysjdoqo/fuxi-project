import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def issue_token() -> str:
    return secrets.token_urlsafe(32)


def get_user_by_token(token: str, db: Session) -> User | None:
    normalized = token.strip()
    if not normalized:
        return None
    return db.query(User).filter(User.token == normalized).first()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    user = get_user_by_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    return user
