from collections import defaultdict
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Question, Subject, User
from utils.ai_access import get_user_deepseek_api_key
from utils.deepseek import get_ai_explanation, has_api_key

router = APIRouter(prefix="/ai", tags=["AI"])

rate_limit_store = defaultdict(list)
RATE_LIMIT = 5
RATE_LIMIT_WINDOW = 60
_rate_limit_lock = threading.Lock()


def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    with _rate_limit_lock:
        rate_limit_store[user_id] = [t for t in rate_limit_store[user_id] if now - t < RATE_LIMIT_WINDOW]
        if len(rate_limit_store[user_id]) >= RATE_LIMIT:
            return False
        rate_limit_store[user_id].append(now)
    return True


@router.get("/explain")
async def explain_question(
    question_id: int = Query(...),
    use_credit: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_rate_limit(current_user.id):
        raise HTTPException(status_code=429, detail="请求过于频繁")

    question = db.query(Question).filter(
        Question.id == question_id,
        Question.user_id == current_user.id,
        Question.deleted_at.is_(None),
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        return {
            "success": False,
            "error": "API_KEY_NOT_CONFIGURED",
            "message": "尚未配置个人 DeepSeek API Key",
        }

    if not has_api_key(api_key):
        return {
            "success": False,
            "error": "API_KEY_NOT_CONFIGURED",
            "message": "尚未配置个人 DeepSeek API Key",
        }

    subject_name = None
    if question.subject_id:
        subject = db.query(Subject).filter(
            Subject.id == question.subject_id,
            Subject.user_id == current_user.id,
        ).first()
        if subject:
            subject_name = subject.name

    explanation = await get_ai_explanation(
        question_content=question.content,
        question_type=question.type,
        options=question.options,
        correct_answer=question.answer,
        subject_name=subject_name,
        api_key=api_key,
    )

    return {
        "success": True,
        "question_id": question_id,
        "explanation": explanation,
    }


@router.get("/check")
def check_api_status(current_user: User = Depends(get_current_user)):
    configured = has_api_key(get_user_deepseek_api_key(current_user))
    return {
        "configured": configured,
        "message": "DeepSeek API Key 已配置" if configured else "尚未配置个人 DeepSeek API Key",
    }
