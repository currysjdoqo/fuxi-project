from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Message, User
from utils.chat_ws import chat_manager, ensure_friendship, serialize_message

router = APIRouter()


class SendMessageRequest(BaseModel):
    receiver_id: int
    content: str


@router.post("/messages/send")
async def send_message(
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    if request.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己发送消息")

    try:
        ensure_friendship(db, current_user.id, request.receiver_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    auto_read = chat_manager.has_active_chat(request.receiver_id, current_user.id)
    message = Message(
        sender_id=current_user.id,
        receiver_id=request.receiver_id,
        content=content,
        is_read=1 if auto_read else 0,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    payload = serialize_message(message)
    await chat_manager.send_to_user(current_user.id, {"type": "message.new", "message": payload})
    await chat_manager.send_to_user(request.receiver_id, {"type": "message.new", "message": payload})
    if auto_read:
        await chat_manager.send_to_user(
            current_user.id,
            {"type": "message.read", "friend_id": request.receiver_id, "message_ids": [message.id]},
        )

    return {"message": "消息发送成功", "message_id": message.id}


@router.get("/messages/{friend_id}")
async def get_messages(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ensure_friendship(db, current_user.id, friend_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    unread_messages = db.query(Message).filter(
        Message.sender_id == friend_id,
        Message.receiver_id == current_user.id,
        Message.is_read == 0,
    ).all()
    unread_ids = [message.id for message in unread_messages]
    for message in unread_messages:
        message.is_read = 1
    db.commit()

    if unread_ids:
        await chat_manager.send_to_user(
            friend_id,
            {"type": "message.read", "friend_id": current_user.id, "message_ids": unread_ids},
        )

    messages = db.query(Message).filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id))
        | ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc(), Message.id.asc()).all()

    return {"messages": [serialize_message(message) for message in messages]}


@router.post("/messages/read/{friend_id}")
async def mark_read(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ensure_friendship(db, current_user.id, friend_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    unread_messages = db.query(Message).filter(
        Message.sender_id == friend_id,
        Message.receiver_id == current_user.id,
        Message.is_read == 0,
    ).all()
    unread_ids = [message.id for message in unread_messages]
    for message in unread_messages:
        message.is_read = 1
    db.commit()

    if unread_ids:
        await chat_manager.send_to_user(
            friend_id,
            {"type": "message.read", "friend_id": current_user.id, "message_ids": unread_ids},
        )

    return {"message": "已标记为已读"}


@router.get("/messages/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Message).filter(
        Message.receiver_id == current_user.id,
        Message.is_read == 0,
    ).count()

    return {"unread_count": count}
