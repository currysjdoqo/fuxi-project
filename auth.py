import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False

    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
            return hmac.compare_digest(derived.hex(), digest_hex)
        except (ValueError, TypeError):
            return False

    # 兼容旧版单次 SHA-256 哈希
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == password_hash


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
