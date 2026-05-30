from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import PracticeRecord, Question, Subject, WrongQuestion

router = APIRouter()


class TrashQuestionOut(BaseModel):
    id: int
    subject_id: Optional[int]
    subject_name: Optional[str]
    type: str
    content: str
    answer: str
    explanation: Optional[str]
    is_important: int = 0
    deleted_at: Optional[datetime]


class RestoreRequest(BaseModel):
    question_ids: List[int]


@router.get("/trash", response_model=List[TrashQuestionOut])
def get_trash(subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Question).filter(Question.deleted_at.is_not(None))
    if subject_id is not None:
        query = query.filter(Question.subject_id == subject_id)

    questions = query.order_by(Question.deleted_at.desc(), Question.id.desc()).all()
    result = []
    for question in questions:
        subject = db.query(Subject).filter(Subject.id == question.subject_id).first() if question.subject_id else None
        result.append({
            "id": question.id,
            "subject_id": question.subject_id,
            "subject_name": subject.name if subject else None,
            "type": question.type,
            "content": question.content,
            "answer": question.answer,
            "explanation": question.explanation,
            "is_important": question.is_important or 0,
            "deleted_at": question.deleted_at,
        })
    return result


@router.post("/trash/restore")
def restore_questions(request: RestoreRequest, db: Session = Depends(get_db)):
    questions = db.query(Question).filter(
        Question.id.in_(request.question_ids),
        Question.deleted_at.is_not(None),
    ).all()
    if not questions:
        raise HTTPException(status_code=404, detail="垃圾桶中没有这些题目")

    for question in questions:
        question.deleted_at = None
    db.commit()
    return {"message": "题目已恢复", "count": len(questions)}


@router.delete("/trash/{question_id}")
def permanently_delete_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.deleted_at.is_not(None),
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不在垃圾桶中")

    db.query(PracticeRecord).filter(PracticeRecord.question_id == question_id).delete()
    db.query(WrongQuestion).filter(WrongQuestion.question_id == question_id).delete()
    db.delete(question)
    db.commit()
    return {"message": "题目已永久删除"}
