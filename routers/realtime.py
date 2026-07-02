from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import database
from auth import get_user_by_token
from models import Message
from utils.chat_ws import chat_manager, ensure_friendship, serialize_message

router = APIRouter()


async def send_socket_error(websocket: WebSocket, detail: str) -> None:
    await websocket.send_json({"type": "error", "detail": detail})


async def handle_open_chat(websocket: WebSocket, user_id: int, friend_id: int) -> None:
    db = database.SessionLocal()
    try:
        ensure_friendship(db, user_id, friend_id)

        unread_messages = db.query(Message).filter(
            Message.sender_id == friend_id,
            Message.receiver_id == user_id,
            Message.is_read == 0,
        ).all()
        unread_ids = [message.id for message in unread_messages]
        for message in unread_messages:
            message.is_read = 1
        db.commit()
    except ValueError as exc:
        await send_socket_error(websocket, str(exc))
        return
    finally:
        db.close()

    chat_manager.set_active_chat(websocket, friend_id)
    await websocket.send_json({"type": "chat.opened", "friend_id": friend_id, "message_ids": unread_ids})
    if unread_ids:
        await chat_manager.send_to_user(
            friend_id,
            {"type": "message.read", "friend_id": user_id, "message_ids": unread_ids},
        )


async def handle_close_chat(websocket: WebSocket) -> None:
    chat_manager.set_active_chat(websocket, None)
    await websocket.send_json({"type": "chat.closed"})


async def handle_send_message(websocket: WebSocket, user_id: int, payload: dict) -> None:
    receiver_id = payload.get("receiver_id")
    content = str(payload.get("content", "")).strip()

    if not isinstance(receiver_id, int):
        await send_socket_error(websocket, "receiver_id 无效")
        return
    if receiver_id == user_id:
        await send_socket_error(websocket, "不能给自己发送消息")
        return
    if not content:
        await send_socket_error(websocket, "消息内容不能为空")
        return

    db = database.SessionLocal()
    try:
        ensure_friendship(db, user_id, receiver_id)
        auto_read = chat_manager.has_active_chat(receiver_id, user_id)
        message = Message(
            sender_id=user_id,
            receiver_id=receiver_id,
            content=content[:500],
            is_read=1 if auto_read else 0,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        message_payload = serialize_message(message)
    except ValueError as exc:
        db.rollback()
        await send_socket_error(websocket, str(exc))
        return
    finally:
        db.close()

    await chat_manager.send_to_user(user_id, {"type": "message.new", "message": message_payload})
    await chat_manager.send_to_user(receiver_id, {"type": "message.new", "message": message_payload})
    if message_payload["is_read"]:
        await chat_manager.send_to_user(
            user_id,
            {"type": "message.read", "friend_id": receiver_id, "message_ids": [message_payload["id"]]},
        )


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    token = (websocket.query_params.get("token") or "").strip()
    if not token:
        await websocket.close(code=4401)
        return

    db = database.SessionLocal()
    try:
        user = get_user_by_token(token, db)
    finally:
        db.close()

    if not user:
        await websocket.close(code=4401)
        return

    await chat_manager.connect(user.id, websocket)
    await websocket.send_json({"type": "connection.ready", "user_id": user.id})

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif event_type == "chat.open":
                friend_id = payload.get("friend_id")
                if not isinstance(friend_id, int):
                    await send_socket_error(websocket, "friend_id 无效")
                else:
                    await handle_open_chat(websocket, user.id, friend_id)
            elif event_type == "chat.close":
                await handle_close_chat(websocket)
            elif event_type == "message.send":
                await handle_send_message(websocket, user.id, payload)
            else:
                await send_socket_error(websocket, "不支持的消息类型")
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket)
    except Exception:
        chat_manager.disconnect(websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
