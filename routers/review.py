from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import re

from database import get_db
from models import WrongQuestion, Question, PracticeRecord, Subject
from routers.settings import get_wrong_question_threshold

router = APIRouter()


class GenerateRequest(BaseModel):
    count: int = 10
    subject_id: Optional[int] = None


class ReviewQuestionOut(BaseModel):
    question_id: int
    type: str
    content: str
    options: dict
    answer: str
    explanation: Optional[str]

    class Config:
        from_attributes = True


class SubmitRequest(BaseModel):
    question_id: int
    user_answer: str
    is_review_mode: bool = True


class SubmitResponse(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: Optional[str]
    removed_from_wrong: bool = False
    remaining_to_remove: int = 0


def normalize_answer(answer: str) -> str:
    return ''.join(answer.strip().upper().split())


def normalize_multi_answer(answer: str) -> str:
    letters = re.findall(r"[A-Z]", answer.upper())
    if not letters:
        return normalize_answer(answer)
    return "".join(sorted(set(letters)))


def is_answer_correct(question_type: str, user_answer: str, correct_answer: str) -> bool:
    if question_type == "multi":
        return normalize_multi_answer(user_answer) == normalize_multi_answer(correct_answer)
    return normalize_answer(user_answer) == normalize_answer(correct_answer)


@router.post("/review/generate", response_model=List[ReviewQuestionOut])
def generate_review_questions(request: GenerateRequest, db: Session = Depends(get_db)):
    query = db.query(WrongQuestion)
    if request.subject_id is not None:
        subject = db.query(Subject).filter(Subject.id == request.subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="科目不存在")
        query = query.join(Question, Question.id == WrongQuestion.question_id).filter(
            Question.subject_id == request.subject_id,
            Question.deleted_at.is_(None),
        )
    else:
        query = query.join(Question, Question.id == WrongQuestion.question_id).filter(Question.deleted_at.is_(None))

    wrong_questions = query.order_by(func.random()).limit(request.count).all()
    
    result = []
    for wq in wrong_questions:
        question = db.query(Question).filter(Question.id == wq.question_id, Question.deleted_at.is_(None)).first()
        if question:
            result.append({
                "question_id": question.id,
                "type": question.type,
                "content": question.content,
                "options": question.options,
                "answer": question.answer,
                "explanation": question.explanation
            })
    
    return result


@router.post("/review/submit", response_model=SubmitResponse)
def submit_review_answer(request: SubmitRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == request.question_id, Question.deleted_at.is_(None)).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    is_correct = is_answer_correct(question.type, request.user_answer, question.answer)
    
    practice_record = PracticeRecord(
        question_id=request.question_id,
        user_answer=request.user_answer,
        is_correct=1 if is_correct else 0
    )
    db.add(practice_record)
    
    threshold = get_wrong_question_threshold()
    removed_from_wrong = False
    remaining_to_remove = 0
    wrong_question = db.query(WrongQuestion).filter(
        WrongQuestion.question_id == request.question_id
    ).first()
    
    if is_correct:
        if wrong_question:
            wrong_question.correct_count = (wrong_question.correct_count or 0) + 1
            wrong_question.last_reviewed_at = datetime.utcnow()
            if wrong_question.correct_count >= threshold:
                db.delete(wrong_question)
                removed_from_wrong = True
            else:
                remaining_to_remove = threshold - wrong_question.correct_count
    else:
        if wrong_question:
            wrong_question.review_count = wrong_question.review_count + 1
            wrong_question.correct_count = 0
            wrong_question.last_reviewed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
        "removed_from_wrong": removed_from_wrong,
        "remaining_to_remove": remaining_to_remove,
    }
