from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any

from database import get_db
from models import Question
from utils.parser import parse_exercise_text

# 创建路由实例
router = APIRouter()


class ImportRequest(BaseModel):
    """
    导入题目请求的 Pydantic 模型
    """
    text: str


class ImportResponse(BaseModel):
    """
    导入题目响应的 Pydantic 模型
    """
    parsed_count: int
    inserted_count: int


def normalize_content(content: str) -> str:
    """
    标准化题干内容：转换为小写并去除所有空白字符
    用于判断题目是否已存在
    """
    return ''.join(content.lower().split())


@router.post("/import", response_model=ImportResponse)
async def import_questions(request: ImportRequest, db: Session = Depends(get_db)):
    """
    导入题目接口
    
    接收包含练习题的文本，解析后批量插入数据库（去重）
    
    请求体:
        {
            "text": "练习题文本内容..."
        }
    
    返回:
        {
            "parsed_count": 解析出的题目总数,
            "inserted_count": 成功插入的题目数量
        }
    """
    # 解析练习题文本
    parsed_questions = parse_exercise_text(request.text)
    parsed_count = len(parsed_questions)
    inserted_count = 0
    
    for q in parsed_questions:
        # 标准化当前题目的题干内容
        normalized_content = normalize_content(q['content'])
        
        # 检查数据库中是否已存在相同内容的题目
        existing_question = db.query(Question).filter(
            normalize_content(Question.content) == normalized_content
        ).first()
        
        if existing_question is None:
            # 创建新题目记录
            new_question = Question(
                type="single",
                content=q['content'],
                options=q['options'],
                answer=q['answer'],
                explanation=q.get('explanation', '')
            )
            db.add(new_question)
            inserted_count += 1
    
    # 提交事务
    db.commit()
    
    return {
        "parsed_count": parsed_count,
        "inserted_count": inserted_count
    }