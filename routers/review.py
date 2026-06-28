from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import PracticeRecord, Question, Subject, User, WrongQuestion
from routers.settings import get_wrong_question_threshold
from utils.answer_normalizer import is_answer_correct

router = APIRouter()


class GenerateRequest(BaseModel):
    count: int = 10
    subject_id: Optional[int] = None


class ReviewSubmission(BaseModel):
    question_id: int
    user_answer: str


class BatchReviewRequest(BaseModel):
    submissions: List[ReviewSubmission]


class ReviewQuestionOut(BaseModel):
    question_id: int
    type: str
    content: str
    options: dict
    answer: str
    explanation: Optional[str]


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


def get_user_question(db: Session, user_id: int, question_id: int) -> Question | None:
    return (
        db.query(Question)
        .filter(
            Question.id == question_id,
            Question.user_id == user_id,
            Question.deleted_at.is_(None),
        )
        .first()
    )


@router.post("/review/generate", response_model=List[ReviewQuestionOut])
def generate_review_questions(
    request: GenerateRequest,
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

    if request.subject_id is not None:
        subject = (
            db.query(Subject)
            .filter(Subject.id == request.subject_id, Subject.user_id == current_user.id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=404, detail="绉戠洰涓嶅瓨鍦?")
        query = query.filter(Question.subject_id == request.subject_id)

    rows = query.order_by(func.random()).limit(request.count).all()
    return [
        {
            "id": question.id,
            "type": question.type,
            "content": question.content,
            "options": question.options,
            "answer": question.answer,
            "explanation": question.explanation,
        }
        for _, question in rows
    ]


@router.post("/review/submit", response_model=SubmitResponse)
def submit_review_answer(
    request: SubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_user_question(db, current_user.id, request.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="棰樼洰涓嶅瓨鍦?")

    is_correct = is_answer_correct(question.type, request.user_answer, question.answer)
    db.add(
        PracticeRecord(
            user_id=current_user.id,
            question_id=request.question_id,
            user_answer=request.user_answer,
            is_correct=1 if is_correct else 0,
        )
    )

    threshold = get_wrong_question_threshold()
    removed_from_wrong = False
    remaining_to_remove = 0
    wrong_question = (
        db.query(WrongQuestion)
        .filter(
            WrongQuestion.question_id == request.question_id,
            WrongQuestion.user_id == current_user.id,
        )
        .first()
    )

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


@router.post("/review/batch-submit")
def batch_submit_review(
    request: BatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    threshold = get_wrong_question_threshold()
    results = []

    for submission in request.submissions:
        question = get_user_question(db, current_user.id, submission.question_id)
        if not question:
            results.append(
                {
                    "question_id": submission.question_id,
                    "error": "棰樼洰涓嶅瓨鍦?",
                }
            )
            continue

        is_correct = is_answer_correct(question.type, submission.user_answer, question.answer)

        db.add(
            PracticeRecord(
                user_id=current_user.id,
                question_id=submission.question_id,
                user_answer=submission.user_answer,
                is_correct=1 if is_correct else 0,
            )
        )

        removed_from_wrong = False
        remaining_to_remove = 0
        wrong_question = (
            db.query(WrongQuestion)
            .filter(
                WrongQuestion.question_id == submission.question_id,
                WrongQuestion.user_id == current_user.id,
            )
            .first()
        )

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

        results.append(
            {
                "question_id": submission.question_id,
                "is_correct": is_correct,
                "correct_answer": question.answer,
                "explanation": question.explanation,
                "removed_from_wrong": removed_from_wrong,
                "remaining_to_remove": remaining_to_remove,
            }
        )

    db.commit()
    return {"results": results}


class UpdateExplanationRequest(BaseModel):
    question_id: int
    explanation: str


@router.post("/review/update-explanation")
def update_question_explanation(
    request: UpdateExplanationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_user_question(db, current_user.id, request.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    question.explanation = request.explanation
    db.commit()
    db.refresh(question)

    return {
        "success": True,
        "question_id": question.id,
        "explanation": question.explanation,
    }
