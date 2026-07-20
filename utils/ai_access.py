from __future__ import annotations

import os
from pathlib import Path

from models import User
from utils.crypto import decrypt_api_key, encrypt_api_key

ENV_PATH = Path(".env")


def _load_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_platform_deepseek_api_key() -> str:
    env_key = os.getenv("DEEPSEEK_API_KEY")
    if env_key:
        return decrypt_api_key(env_key)

    loaded_key = _load_env_values().get("DEEPSEEK_API_KEY", "")
    return decrypt_api_key(loaded_key)


def set_platform_deepseek_api_key(api_key: str) -> str:
    encrypted = encrypt_api_key(api_key)
    values = _load_env_values()
    values["DEEPSEEK_API_KEY"] = encrypted
    ENV_PATH.write_text(
        "\n".join(f'{key}="{value}"' for key, value in values.items()) + "\n",
        encoding="utf-8",
    )
    os.environ["DEEPSEEK_API_KEY"] = encrypted
    return encrypted


def get_user_deepseek_api_key(user: User) -> str:
    if user.ai_provider != "custom" or not user.custom_ai_api_key_encrypted:
        return ""
    return decrypt_api_key(user.custom_ai_api_key_encrypted)


def set_user_deepseek_api_key(user: User, api_key: str) -> None:
    user.custom_ai_api_key_encrypted = encrypt_api_key(api_key)
    user.ai_provider = "custom"


def clear_user_deepseek_api_key(user: User) -> None:
    user.custom_ai_api_key_encrypted = None
    if user.ai_provider == "custom":
        user.ai_provider = "platform"


def get_effective_deepseek_api_key(user: User) -> str:
    user_key = get_user_deepseek_api_key(user)
    if user_key:
        return user_key
    return get_platform_deepseek_api_key()
