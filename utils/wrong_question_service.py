"""
错题处理共享逻辑。
被 routers/practice.py 和 routers/review.py 调用，避免重复实现。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models import WrongQuestion


_UNSET = object()


def update_wrong_question_state(
    db: Session,
    user_id: int,
    question_id: int,
    is_correct: bool,
    threshold: int,
    wrong_question=_UNSET,
) -> tuple[bool, int]:
    """
    根据作答结果更新错题记录。

    :param wrong_question: 批量场景下由调用方预先查好的错题记录（None 表示确认不存在），
        传了就不再单独查询，避免 N+1。
    :return: (removed_from_wrong, remaining_to_remove)
    """
    if wrong_question is _UNSET:
        wrong_question = (
            db.query(WrongQuestion)
            .filter(
                WrongQuestion.question_id == question_id,
                WrongQuestion.user_id == user_id,
            )
            .first()
        )

    if not is_correct:
        if wrong_question:
            wrong_question.review_count = wrong_question.review_count + 1
            wrong_question.correct_count = 0
            wrong_question.last_reviewed_at = datetime.utcnow()
        else:
            db.add(
                WrongQuestion(
                    user_id=user_id,
                    question_id=question_id,
                    correct_count=0,
                )
            )
        return False, 0

    # 答对了
    if wrong_question:
        wrong_question.correct_count = (wrong_question.correct_count or 0) + 1
        wrong_question.last_reviewed_at = datetime.utcnow()
        if wrong_question.correct_count >= threshold:
            db.delete(wrong_question)
            return True, 0
        return False, threshold - wrong_question.correct_count

    return False, 0
