from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import PracticeRecord, Question, Subject, User, WrongQuestion

router = APIRouter()


class WrongQuestionOut(BaseModel):
    question_id: int
    subject_id: Optional[int]
    type: str
    content: str
    options: dict
    answer: str
    explanation: Optional[str]
    added_at: str
    review_count: int
    last_user_answer: Optional[str]

    class Config:
        from_attributes = True


@router.get("/wrong-questions", response_model=List[WrongQuestionOut])
def get_wrong_questions(
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(WrongQuestion, Question)
        .join(
            Question,
            (Question.id == WrongQuestion.question_id)
            & (Question.user_id == current_user.id)
            & (Question.deleted_at.is_(None)),
        )
        .filter(WrongQuestion.user_id == current_user.id)
    )

    if subject_id is not None:
        subject = (
            db.query(Subject)
            .filter(Subject.id == subject_id, Subject.user_id == current_user.id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=404, detail="科目不存在")
        query = query.filter(Question.subject_id == subject_id)

    rows = query.order_by(WrongQuestion.added_at.desc()).all()

    # 一次查出所有错题「最近一次练习作答」，避免每道错题单独查一次
    last_answers = {}
    question_ids = [wrong_question.question_id for wrong_question, _ in rows]
    if question_ids:
        latest = (
            db.query(
                PracticeRecord.question_id.label("question_id"),
                func.max(PracticeRecord.practiced_at).label("last_time"),
            )
            .filter(
                PracticeRecord.user_id == current_user.id,
                PracticeRecord.question_id.in_(question_ids),
            )
            .group_by(PracticeRecord.question_id)
            .subquery()
        )
        latest_rows = (
            db.query(PracticeRecord.question_id, PracticeRecord.user_answer)
            .join(
                latest,
                and_(
                    PracticeRecord.question_id == latest.c.question_id,
                    PracticeRecord.practiced_at == latest.c.last_time,
                ),
            )
            .filter(PracticeRecord.user_id == current_user.id)
            .all()
        )
        for question_id, user_answer in latest_rows:
            last_answers[question_id] = user_answer

    result = []
    for wrong_question, question in rows:
        result.append(
            {
                "question_id": wrong_question.question_id,
                "subject_id": question.subject_id,
                "type": question.type,
                "content": question.content,
                "options": question.options,
                "answer": question.answer,
                "explanation": question.explanation,
                "added_at": wrong_question.added_at.isoformat(),
                "review_count": wrong_question.review_count,
                "last_user_answer": last_answers.get(wrong_question.question_id),
            }
        )
    return result


@router.delete("/wrong-questions/{question_id}")
def remove_wrong_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wrong_question = (
        db.query(WrongQuestion)
        .filter(
            WrongQuestion.question_id == question_id,
            WrongQuestion.user_id == current_user.id,
        )
        .first()
    )
    if not wrong_question:
        raise HTTPException(status_code=404, detail="错题不存在")
    db.delete(wrong_question)
    db.commit()
    return {"message": "删除成功"}
