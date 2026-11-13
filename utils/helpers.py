"""
通用辅助函数。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from models import Question


def get_user_question(db: Session, user_id: int, question_id: int) -> Question | None:
    """按归属用户安全地查询未删除题目。"""
    return (
        db.query(Question)
        .filter(
            Question.id == question_id,
            Question.user_id == user_id,
            Question.deleted_at.is_(None),
        )
        .first()
    )
