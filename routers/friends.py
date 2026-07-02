from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Friendship, Message, User
from utils.chat_ws import chat_manager

router = APIRouter()


class SendFriendRequest(BaseModel):
    user_code: str


class RespondFriendRequest(BaseModel):
    friend_id: int


def get_friendship(db: Session, user_id: int, friend_id: int) -> Friendship | None:
    return db.query(Friendship).filter(
        ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id))
        | ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
    ).first()


@router.post("/friends/request")
async def send_friend_request(
    request: SendFriendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_code = request.user_code.strip()
    if len(user_code) != 10 or not user_code.isdigit():
        raise HTTPException(status_code=400, detail="好友 ID 必须是 10 位数字")

    target_user = db.query(User).filter(User.user_code == user_code).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能添加自己为好友")

    existing = get_friendship(db, current_user.id, target_user.id)
    if existing:
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="好友请求已发送")
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="对方已经是你的好友")
        raise HTTPException(status_code=400, detail="该好友请求已被拒绝，请稍后再试")

    friendship = Friendship(
        user_id=current_user.id,
        friend_id=target_user.id,
        status="pending",
    )
    db.add(friendship)
    db.commit()

    payload = {
        "type": "friendship.updated",
        "reason": "pending",
        "friend_id": target_user.id,
    }
    await chat_manager.send_to_user(current_user.id, payload)
    await chat_manager.send_to_user(target_user.id, payload)

    return {"message": "好友请求已发送", "friend_id": target_user.id}


@router.post("/friends/accept")
async def accept_friend_request(
    request: RespondFriendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    friendship = db.query(Friendship).filter(
        Friendship.user_id == request.friend_id,
        Friendship.friend_id == current_user.id,
        Friendship.status == "pending",
    ).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="好友请求不存在")

    friendship.status = "accepted"
    db.commit()

    payload = {
        "type": "friendship.updated",
        "reason": "accepted",
        "friend_id": request.friend_id,
    }
    await chat_manager.send_to_user(current_user.id, payload)
    await chat_manager.send_to_user(request.friend_id, payload)

    return {"message": "已同意好友请求"}


@router.post("/friends/reject")
async def reject_friend_request(
    request: RespondFriendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    friendship = db.query(Friendship).filter(
        Friendship.user_id == request.friend_id,
        Friendship.friend_id == current_user.id,
        Friendship.status == "pending",
    ).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="好友请求不存在")

    friendship.status = "rejected"
    db.commit()

    payload = {
        "type": "friendship.updated",
        "reason": "rejected",
        "friend_id": request.friend_id,
    }
    await chat_manager.send_to_user(current_user.id, payload)
    await chat_manager.send_to_user(request.friend_id, payload)

    return {"message": "已拒绝好友请求"}


@router.get("/friends/list")
def get_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    friendships = db.query(Friendship).filter(
        ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
        Friendship.status == "accepted",
    ).all()

    result = []
    for friendship in friendships:
        friend_id = friendship.friend_id if friendship.user_id == current_user.id else friendship.user_id
        friend = db.query(User).filter(User.id == friend_id).first()
        if not friend:
            continue

        unread_count = db.query(func.count(Message.id)).filter(
            Message.sender_id == friend.id,
            Message.receiver_id == current_user.id,
            Message.is_read == 0,
        ).scalar() or 0

        result.append({
            "user_id": friend.id,
            "username": friend.username,
            "avatar": friend.avatar,
            "signature": friend.signature,
            "user_code": friend.user_code,
            "unread_count": unread_count,
        })

    result.sort(key=lambda item: (-item["unread_count"], item["username"].lower()))
    return {"friends": result}


@router.get("/friends/pending")
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requests = db.query(Friendship).filter(
        Friendship.friend_id == current_user.id,
        Friendship.status == "pending",
    ).all()

    result = []
    for friendship in requests:
        user = db.query(User).filter(User.id == friendship.user_id).first()
        if not user:
            continue

        result.append({
            "user_id": user.id,
            "username": user.username,
            "avatar": user.avatar,
            "signature": user.signature,
            "user_code": user.user_code,
            "request_id": friendship.id,
        })

    return {"pending": result}


@router.delete("/friends/{friend_id}")
def remove_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    friendship = get_friendship(db, current_user.id, friend_id)
    if not friendship:
        raise HTTPException(status_code=404, detail="好友关系不存在")

    db.delete(friendship)
    db.commit()

    return {"message": "好友已删除"}


@router.get("/users/search")
def search_user(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_code = code.strip()
    if len(user_code) != 10 or not user_code.isdigit():
        raise HTTPException(status_code=400, detail="好友 ID 必须是 10 位数字")

    user = db.query(User).filter(User.user_code == user_code).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能搜索自己")

    friendship = get_friendship(db, current_user.id, user.id)
    return {
        "user_id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        "signature": user.signature,
        "user_code": user.user_code,
        "friend_status": friendship.status if friendship else None,
    }
