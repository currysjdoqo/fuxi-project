from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import re

from database import get_db
from models import Question, PracticeRecord, Subject, WrongQuestion
from routers.settings import get_wrong_question_threshold
from schemas import QuestionOut

router = APIRouter()


class SubmitRequest(BaseModel):
    question_id: int
    user_answer: str


class SubmitResponse(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: Optional[str]
    removed_from_wrong: bool = False
    remaining_to_remove: int = 0


class QuestionTypeUpdateRequest(BaseModel):
    type: str


class QuestionImportantUpdateRequest(BaseModel):
    is_important: bool


class QuestionAnswerUpdateRequest(BaseModel):
    answer: str


class BatchDeleteRequest(BaseModel):
    question_ids: List[int]


def normalize_answer(answer: str) -> str:
    return ''.join(answer.strip().upper().split())


def normalize_multi_answer(answer: str) -> str:
    letters = re.findall(r"[A-Z]", answer.upper())
    if not letters:
        return normalize_answer(answer)
    return "".join(sorted(set(letters)))


def normalize_judge_answer(answer: str) -> str:
    compact = "".join(answer.strip().upper().split())
    if compact in {"对", "正确", "TRUE", "T", "YES", "Y", "A", "√", "✓", "✔"}:
        return "T"
    if compact in {"错", "错误", "FALSE", "F", "NO", "N", "B", "×", "✕", "✖", "X"}:
        return "F"
    return compact


def normalize_standard_answer(question_type: str, answer: str) -> str:
    raw = answer.strip()
    if question_type == "multi":
        return normalize_multi_answer(raw)
    if question_type == "single":
        match = re.search(r"[A-Z]", raw.upper())
        return match.group(0) if match else normalize_answer(raw)
    if question_type == "judge":
        return normalize_judge_answer(raw)
    return raw


def is_answer_correct(question_type: str, user_answer: str, correct_answer: str) -> bool:
    if question_type == "multi":
        return normalize_multi_answer(user_answer) == normalize_multi_answer(correct_answer)
    return normalize_answer(user_answer) == normalize_answer(correct_answer)


def normalize_question_type(question_type: str) -> str:
    return question_type if question_type in {"single", "multi", "judge", "fill", "short", "code"} else "single"


@router.get("/questions", response_model=List[QuestionOut])
def get_questions(
    skip: int = 0,
    limit: int = 10,
    subject_id: Optional[int] = None,
    question_type: Optional[str] = None,
    important_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Question)
    query = query.filter(Question.deleted_at.is_(None))
    if subject_id is not None:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="科目不存在")
        query = query.filter(Question.subject_id == subject_id)
    if question_type and question_type != "all":
        query = query.filter(Question.type == normalize_question_type(question_type))
    if important_only:
        query = query.filter(Question.is_important == 1)

    questions = query.order_by(Question.id.asc()).offset(skip).limit(limit).all()
    return questions


@router.patch("/questions/{question_id}/type", response_model=QuestionOut)
def update_question_type(question_id: int, request: QuestionTypeUpdateRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id, Question.deleted_at.is_(None)).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    question.type = normalize_question_type(request.type)
    if question.type == "judge" and not question.options:
        question.options = {"T": "正确", "F": "错误"}
    db.commit()
    db.refresh(question)
    return question


@router.patch("/questions/{question_id}/important", response_model=QuestionOut)
def update_question_important(question_id: int, request: QuestionImportantUpdateRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id, Question.deleted_at.is_(None)).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    question.is_important = 1 if request.is_important else 0
    db.commit()
    db.refresh(question)
    return question


@router.patch("/questions/{question_id}/answer", response_model=QuestionOut)
def update_question_answer(question_id: int, request: QuestionAnswerUpdateRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id, Question.deleted_at.is_(None)).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    normalized = normalize_standard_answer(question.type, request.answer)
    if not normalized:
        raise HTTPException(status_code=400, detail="答案不能为空")

    question.answer = normalized
    db.commit()
    db.refresh(question)
    return question


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id, Question.deleted_at.is_(None)).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    question.deleted_at = datetime.utcnow()
    db.query(WrongQuestion).filter(WrongQuestion.question_id == question_id).delete()
    db.commit()

    return {"message": "题目已移入垃圾桶"}


@router.post("/questions/batch-delete")
def batch_delete_questions(request: BatchDeleteRequest, db: Session = Depends(get_db)):
    question_ids = request.question_ids
    if not question_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的题目")

    questions = db.query(Question).filter(
        Question.id.in_(question_ids),
        Question.deleted_at.is_(None)
    ).all()
    if not questions:
        raise HTTPException(status_code=404, detail="题目不存在")

    for question in questions:
        question.deleted_at = datetime.utcnow()
        db.query(WrongQuestion).filter(WrongQuestion.question_id == question.id).delete()
    db.commit()
    return {"message": "题目已批量移入垃圾桶", "count": len(questions)}


@router.post("/practice/submit", response_model=SubmitResponse)
def submit_practice(request: SubmitRequest, db: Session = Depends(get_db)):
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

    if not is_correct:
        if wrong_question:
            wrong_question.review_count = wrong_question.review_count + 1
            wrong_question.correct_count = 0
            wrong_question.last_reviewed_at = datetime.utcnow()
        else:
            new_wrong = WrongQuestion(
                question_id=request.question_id,
                correct_count=0,
            )
            db.add(new_wrong)
    else:
        if wrong_question:
            wrong_question.correct_count = (wrong_question.correct_count or 0) + 1
            wrong_question.last_reviewed_at = datetime.utcnow()
            if wrong_question.correct_count >= threshold:
                db.delete(wrong_question)
                removed_from_wrong = True
            else:
                remaining_to_remove = threshold - wrong_question.correct_count
    
    db.commit()
    
    return {
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
        "removed_from_wrong": removed_from_wrong,
        "remaining_to_remove": remaining_to_remove,
    }
