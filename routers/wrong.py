from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
            raise HTTPException(status_code=404, detail="绉戠洰涓嶅瓨鍦?")
        query = query.filter(Question.subject_id == subject_id)

    rows = query.order_by(WrongQuestion.added_at.desc()).all()
    result = []
    for wrong_question, question in rows:
        last_record = (
            db.query(PracticeRecord)
            .filter(
                PracticeRecord.question_id == wrong_question.question_id,
                PracticeRecord.user_id == current_user.id,
            )
            .order_by(PracticeRecord.practiced_at.desc())
            .first()
        )
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
                "last_user_answer": last_record.user_answer if last_record else None,
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
        raise HTTPException(status_code=404, detail="閿欓涓嶅瓨鍦?")
    db.delete(wrong_question)
    db.commit()
    return {"message": "鍒犻櫎鎴愬姛"}
