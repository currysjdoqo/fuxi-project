import json
import os
from pathlib import Path
from urllib import error, request

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import PracticeRecord, Question, Subject, WrongQuestion

router = APIRouter()

ENV_PATH = Path(".env")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
WRONG_THRESHOLD_KEY = "WRONG_QUESTION_REMOVE_THRESHOLD"
DEFAULT_WRONG_THRESHOLD = 1


class ApiKeyRequest(BaseModel):
    api_key: str


class WrongThresholdRequest(BaseModel):
    threshold: int


class AiExplainRequest(BaseModel):
    question_id: int


class AiExplainResponse(BaseModel):
    explanation: str
    source: str


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
    return os.getenv("DEEPSEEK_API_KEY") or _load_env_values().get("DEEPSEEK_API_KEY", "")


def get_wrong_question_threshold() -> int:
    raw_value = os.getenv(WRONG_THRESHOLD_KEY) or _load_env_values().get(WRONG_THRESHOLD_KEY, str(DEFAULT_WRONG_THRESHOLD))
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
def get_settings():
    return {
        "has_deepseek_api_key": bool(_get_deepseek_api_key()),
        "wrong_question_remove_threshold": get_wrong_question_threshold(),
    }


@router.post("/settings/deepseek-key")
def save_deepseek_key(request_body: ApiKeyRequest):
    api_key = request_body.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 不能为空")
    _write_env_value("DEEPSEEK_API_KEY", api_key)
    os.environ["DEEPSEEK_API_KEY"] = api_key
    return {"message": "DeepSeek API Key 已保存"}


@router.post("/settings/wrong-threshold")
def save_wrong_threshold(request_body: WrongThresholdRequest):
    threshold = request_body.threshold
    if threshold < 1 or threshold > 10:
        raise HTTPException(status_code=400, detail="阈值必须在 1 到 10 之间")
    _write_env_value(WRONG_THRESHOLD_KEY, str(threshold))
    os.environ[WRONG_THRESHOLD_KEY] = str(threshold)
    return {"message": "错题移除阈值已保存", "threshold": threshold}


@router.delete("/data")
def clear_all_data(db: Session = Depends(get_db)):
    db.query(PracticeRecord).delete()
    db.query(WrongQuestion).delete()
    db.query(Question).delete()
    db.query(Subject).delete()
    db.commit()
    return {"message": "所有数据已清空"}


@router.post("/ai/explain", response_model=AiExplainResponse)
def explain_question(request_body: AiExplainRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == request_body.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    api_key = _get_deepseek_api_key()
    if not api_key:
        fallback = question.explanation or "暂无解析。请先在设置页配置 DeepSeek API Key 后再使用 AI 讲解。"
        return {"explanation": fallback, "source": "local"}

    option_text = "\n".join(f"{key}. {value}" for key, value in sorted(question.options.items()))
    prompt = (
        "请用中文给学生讲解这道单选题，说明正确答案为什么正确，以及其他选项为什么不合适。"
        "讲解要简洁、聚焦知识点。\n\n"
        f"题干：{question.content}\n"
        f"选项：\n{option_text}\n"
        f"正确答案：{question.answer}\n"
        f"已有解析：{question.explanation or '无'}"
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一名耐心、严谨的课程助教。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "stream": False,
    }

    http_request = request.Request(
        DEEPSEEK_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore") or str(exc)
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败：{detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败：{exc}") from exc

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise HTTPException(status_code=502, detail="DeepSeek 未返回有效讲解")
    return {"explanation": content, "source": "deepseek"}
