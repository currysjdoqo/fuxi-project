from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import check_auth_rate_limit, get_current_user
from database import get_db
from models import Question, Subject, User
from utils.ai_access import get_user_deepseek_api_key
from utils.deepseek import get_ai_explanation, has_api_key

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/explain")
async def explain_question(
    question_id: int = Query(...),
    use_credit: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_auth_rate_limit(f"ai:{current_user.id}"):
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
