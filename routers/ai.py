"""
AI 讲解 API 路由
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional
import time
from collections import defaultdict

from database import get_db
from models import Question, Subject
from utils.deepseek import get_ai_explanation, has_api_key

router = APIRouter(prefix="/ai", tags=["AI讲解"])

# 简单的内存速率限制器
rate_limit_store = defaultdict(list)
RATE_LIMIT = 5
RATE_LIMIT_WINDOW = 60


def check_rate_limit(ip: str) -> bool:
    """检查速率限制"""
    now = time.time()
    # 移除过期的请求记录
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < RATE_LIMIT_WINDOW]
    # 检查是否超过限制
    if len(rate_limit_store[ip]) >= RATE_LIMIT:
        return False
    # 记录当前请求
    rate_limit_store[ip].append(now)
    return True


@router.get("/explain")
async def explain_question(
    question_id: int = Query(...),
    request: Request = None
):
    """获取题目讲解（每分钟最多调用 5 次）"""
    # 获取客户端 IP
    client_ip = "default"
    if request:
        client_ip = request.client.host if request.client else "default"
    
    # 速率限制检查
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试（每分钟最多 5 次）"
        )
    
    db = next(get_db())

    question = db.query(Question).filter(
        Question.id == question_id,
        Question.deleted_at.is_(None)
    ).first()

    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    # 检查是否配置了 API Key
    if not has_api_key():
        return {
            "success": False,
            "error": "API_KEY_NOT_CONFIGURED",
            "message": "尚未配置 DeepSeek API Key，请在设置页面配置后重试。"
        }

    # 获取科目名称
    subject_name = None
    if question.subject_id:
        subject = db.query(Subject).filter(
            Subject.id == question.subject_id
        ).first()
        if subject:
            subject_name = subject.name

    # 调用 DeepSeek API
    explanation = await get_ai_explanation(
        question_content=question.content,
        question_type=question.type,
        options=question.options,
        correct_answer=question.answer,
        subject_name=subject_name
    )

    return {
        "success": True,
        "question_id": question_id,
        "explanation": explanation
    }


@router.get("/check")
def check_api_status():
    """检查 API 配置状态"""
    configured = has_api_key()
    return {
        "configured": configured,
        "message": "DeepSeek API Key 已配置" if configured else "尚未配置 DeepSeek API Key"
    }
