import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, verify_password
from database import get_db
from models import PracticeRecord, Question, Subject, User, WrongQuestion
from utils.crypto import encrypt_api_key, decrypt_api_key

router = APIRouter()

ENV_PATH = Path(".env")
WRONG_THRESHOLD_KEY = "WRONG_QUESTION_REMOVE_THRESHOLD"
DEFAULT_WRONG_THRESHOLD = 1


class ApiKeyRequest(BaseModel):
    api_key: str


class WrongThresholdRequest(BaseModel):
    threshold: int


class ClearDataRequest(BaseModel):
    password: str


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


def _write_env_value(key: str, value: str) -> None:
    values = _load_env_values()
    values[key] = value
    ENV_PATH.write_text(
        "\n".join(f'{env_key}="{env_value}"' for env_key, env_value in values.items()) + "\n",
        encoding="utf-8",
    )


def _get_deepseek_api_key() -> str:
    env_key = os.getenv("DEEPSEEK_API_KEY")
    if env_key:
        return decrypt_api_key(env_key)
    
    loaded_key = _load_env_values().get("DEEPSEEK_API_KEY", "")
    return decrypt_api_key(loaded_key)


def get_wrong_question_threshold() -> int:
    raw_value = os.getenv(WRONG_THRESHOLD_KEY) or _load_env_values().get(
        WRONG_THRESHOLD_KEY,
        str(DEFAULT_WRONG_THRESHOLD),
    )
    try:
        threshold = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_WRONG_THRESHOLD

    if threshold < 1:
        return 1
    if threshold > 10:
        return 10
    return threshold


@router.get("/settings")
def get_settings(current_user: User = Depends(get_current_user)):
    return {
        "has_deepseek_api_key": bool(_get_deepseek_api_key()),
        "wrong_question_remove_threshold": get_wrong_question_threshold(),
    }


@router.post("/settings/deepseek-key")
def save_deepseek_key(
    request_body: ApiKeyRequest,
    current_user: User = Depends(get_current_user),
):
    api_key = request_body.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 不能为空")

    encrypted_key = encrypt_api_key(api_key)
    _write_env_value("DEEPSEEK_API_KEY", encrypted_key)
    os.environ["DEEPSEEK_API_KEY"] = encrypted_key
    return {"message": "DeepSeek API Key 已加密保存"}


@router.post("/settings/wrong-threshold")
def save_wrong_threshold(
    request_body: WrongThresholdRequest,
    current_user: User = Depends(get_current_user),
):
    threshold = request_body.threshold
    if threshold < 1 or threshold > 10:
        raise HTTPException(status_code=400, detail="阈值必须在 1 到 10 之间")

    _write_env_value(WRONG_THRESHOLD_KEY, str(threshold))
    os.environ[WRONG_THRESHOLD_KEY] = str(threshold)
    return {"message": "错题移除阈值已保存", "threshold": threshold}


@router.delete("/data")
def clear_all_data(
    request_body: ClearDataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    password = request_body.password.strip()
    if not password:
        raise HTTPException(status_code=400, detail="请输入当前密码")
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="密码错误，无法清空数据")

    db.query(PracticeRecord).filter(PracticeRecord.user_id == current_user.id).delete()
    db.query(WrongQuestion).filter(WrongQuestion.user_id == current_user.id).delete()
    db.query(Question).filter(Question.user_id == current_user.id).delete()
    db.query(Subject).filter(Subject.user_id == current_user.id).delete()
    db.commit()
    return {"message": "所有数据已清空"}
