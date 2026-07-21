from __future__ import annotations

from models import User
from utils.crypto import decrypt_api_key, encrypt_api_key


def get_user_deepseek_api_key(user: User) -> str:
    if not user.custom_ai_api_key_encrypted:
        return ""
    return decrypt_api_key(user.custom_ai_api_key_encrypted)


def set_user_deepseek_api_key(user: User, api_key: str) -> None:
    user.custom_ai_api_key_encrypted = encrypt_api_key(api_key)


def clear_user_deepseek_api_key(user: User) -> None:
    user.custom_ai_api_key_encrypted = None


def get_effective_deepseek_api_key(user: User) -> str:
    return get_user_deepseek_api_key(user)
