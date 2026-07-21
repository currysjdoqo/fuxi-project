from __future__ import annotations

from collections import defaultdict
from datetime import timezone
import html

from fastapi import WebSocket
from sqlalchemy.orm import Session

from models import Friendship, Message


def escape_html(content: str) -> str:
    return html.escape(content, quote=True)


def sanitize_message_content(content: str) -> str:
    sanitized = escape_html(content)
    sanitized = sanitized.replace("\n", "<br>")
    return sanitized


def serialize_message(message: Message) -> dict:
    created_at = message.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "content": sanitize_message_content(message.content),
        "is_read": message.is_read,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }


def ensure_friendship(db: Session, current_user_id: int, friend_id: int) -> None:
    is_friend = db.query(Friendship).filter(
        ((Friendship.user_id == current_user_id) & (Friendship.friend_id == friend_id))
        | ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user_id)),
        Friendship.status == "accepted",
    ).first()
    if not is_friend:
        raise ValueError("对方不是你的好友")


class ChatConnectionManager:
    def __init__(self) -> None:
        self.user_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self.connection_users: dict[WebSocket, int] = {}
        self.active_chats: dict[WebSocket, int | None] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.user_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        self.active_chats[websocket] = None

    def disconnect(self, websocket: WebSocket) -> None:
        user_id = self.connection_users.pop(websocket, None)
        self.active_chats.pop(websocket, None)
        if user_id is None:
            return

        sockets = self.user_connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self.user_connections.pop(user_id, None)

    def set_active_chat(self, websocket: WebSocket, friend_id: int | None) -> None:
        if websocket in self.connection_users:
            self.active_chats[websocket] = friend_id

    def has_active_chat(self, user_id: int, friend_id: int) -> bool:
        for websocket in self.user_connections.get(user_id, set()):
            if self.active_chats.get(websocket) == friend_id:
                return True
        return False

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        stale_connections = []
        for websocket in list(self.user_connections.get(user_id, set())):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            self.disconnect(websocket)


chat_manager = ChatConnectionManager()
