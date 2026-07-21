import random
import string
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import check_auth_rate_limit, get_current_user, hash_password, issue_token, verify_password
from database import get_db
from models import User
from utils.billing import ensure_user_invite_code


def generate_user_code(db: Session) -> str:
    while True:
        code = "".join(random.choices(string.digits, k=10))
        existing = db.query(User).filter(User.user_code == code).first()
        if not existing:
            return code


router = APIRouter()

UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class AuthRequest(BaseModel):
    username: str
    password: str
    invite_code: str | None = None


class AuthResponse(BaseModel):
    token: str
    user_id: int
    username: str
    user_code: str
    invite_code: str | None = None


class UpdateProfileRequest(BaseModel):
    signature: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/auth/register", response_model=AuthResponse)
def register(request: AuthRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    password = request.password.strip()
    invite_code = (request.invite_code or "").strip().upper()

    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    if not check_auth_rate_limit(f"register:{username}"):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    inviter = None
    if invite_code:
        inviter = db.query(User).filter(User.invite_code == invite_code).first()
        if not inviter:
            raise HTTPException(status_code=400, detail="邀请码无效")

    token = issue_token()
    user_code = generate_user_code(db)
    user = User(
        username=username,
        password_hash=hash_password(password),
        token=token,
        user_code=user_code,
        invited_by_id=inviter.id if inviter else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_user_invite_code(db, user)
    return {
        "token": token,
        "user_id": user.id,
        "username": user.username,
        "user_code": user_code,
        "invite_code": user.invite_code,
    }


@router.post("/auth/login", response_model=AuthResponse)
def login(request: AuthRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    password = request.password.strip()

    if not check_auth_rate_limit(f"login:{username}"):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="登录失败，请检查用户名和密码")

    if not user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password(password)
    user.token = issue_token()
    db.commit()
    db.refresh(user)
    ensure_user_invite_code(db, user)
    return {
        "token": user.token,
        "user_id": user.id,
        "username": user.username,
        "user_code": user.user_code,
        "invite_code": user.invite_code,
    }


@router.post("/auth/refresh")
def refresh_token(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的Token")

    token = authorization.split(" ", 1)[1].strip()
    user = db.query(User).filter(User.token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="无效的Token")

    user.token = issue_token()
    db.commit()
    db.refresh(user)
    return {
        "token": user.token,
        "user_id": user.id,
        "username": user.username,
    }


@router.get("/auth/me")
def me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_user_invite_code(db, current_user)
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "avatar": current_user.avatar,
        "signature": current_user.signature,
        "user_code": current_user.user_code,
        "invite_code": current_user.invite_code,
        "invited_by_id": current_user.invited_by_id,
        "balance_cents": current_user.balance_cents or 0,
        "call_credits": current_user.call_credits or 0,
        "member_expires_at": current_user.member_expires_at.isoformat() if current_user.member_expires_at else None,
        "member_calls_remaining": current_user.member_calls_remaining or 0,
    }


@router.put("/auth/profile")
def update_profile(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request.signature is not None:
        current_user.signature = request.signature.strip()
    db.commit()
    db.refresh(current_user)
    ensure_user_invite_code(db, current_user)
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "avatar": current_user.avatar,
        "signature": current_user.signature,
        "user_code": current_user.user_code,
        "invite_code": current_user.invite_code,
    }


@router.post("/auth/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="只支持 JPG、PNG、GIF、WebP 格式的图片")
    if file.size > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 2MB")

    filename = f"avatar_{current_user.id}{ext}"
    file_path = UPLOAD_DIR / filename
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    current_user.avatar = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(current_user)
    return {"user_id": current_user.id, "avatar": current_user.avatar}


@router.post("/auth/password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    old_password = request.old_password.strip()
    new_password = request.new_password.strip()
    if not old_password:
        raise HTTPException(status_code=400, detail="请输入旧密码")
    if not new_password:
        raise HTTPException(status_code=400, detail="请输入新密码")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if old_password == new_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="旧密码错误")

    current_user.password_hash = hash_password(new_password)
    db.commit()
    return {"message": "密码修改成功"}
