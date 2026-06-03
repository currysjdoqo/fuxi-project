from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, hash_password, issue_token, verify_password
from database import get_db
from models import User

router = APIRouter()


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    username: str


@router.post("/auth/register", response_model=AuthResponse)
def register(request: AuthRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    password = request.password.strip()
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    token = issue_token()
    user = User(username=username, password_hash=hash_password(password), token=token)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": token, "user_id": user.id, "username": user.username}


@router.post("/auth/login", response_model=AuthResponse)
def login(request: AuthRequest, db: Session = Depends(get_db)):
    username = request.username.strip()
    password = request.password.strip()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.token = issue_token()
    db.commit()
    db.refresh(user)
    return {"token": user.token, "user_id": user.id, "username": user.username}


@router.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "username": current_user.username}
