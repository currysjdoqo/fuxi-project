from datetime import datetime
from typing import List, Optional
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Chapter, PracticeRecord, Question, Subject, User, WrongQuestion
from routers.settings import get_wrong_question_threshold
from schemas import QuestionOut
from utils.answer_normalizer import (
    is_answer_correct,
    normalize_answer,
    normalize_judge_answer,
    normalize_multi_answer,
    normalize_question_type,
    normalize_standard_answer,
)
from utils.helpers import get_user_question
from utils.wrong_question_service import update_wrong_question_state

router = APIRouter()


def apply_chapter_filter(query, db: Session, current_user: User, chapter_id: Optional[int]):
    """按章节过滤题目。chapter_id 为 0 表示未分章，正数表示指定章节。"""
    if chapter_id is None:
        return query
    if chapter_id == 0:
        return query.filter(Question.chapter_id.is_(None) | (Question.chapter_id == 0))

    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.user_id == current_user.id,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return query.filter(Question.chapter_id == chapter_id)


class SubmitRequest(BaseModel):
    question_id: int
    user_answer: str
    self_evaluation: Optional[bool] = None


class SubmitResponse(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: Optional[str]
    removed_from_wrong: bool = False
    remaining_to_remove: int = 0
    self_evaluation_required: bool = False
    evaluated: bool = True


class QuestionTypeUpdateRequest(BaseModel):
    type: str


class QuestionImportantUpdateRequest(BaseModel):
    is_important: bool


class QuestionAnswerUpdateRequest(BaseModel):
    answer: str


class QuestionOptionsUpdateRequest(BaseModel):
    options: dict[str, str]


class BatchDeleteRequest(BaseModel):
    question_ids: List[int]


class BatchSubmitRequest(BaseModel):
    submissions: List[SubmitRequest]


def normalize_question_options(question_type: str, options: dict[str, str]) -> dict[str, str]:
    if question_type in {"single", "multi"}:
        normalized: dict[str, str] = {}
        for key, value in options.items():
            k = str(key).strip().upper()
            v = str(value).strip()
            if not k or not v:
                continue
            if not re.fullmatch(r"[A-Z]", k):
                continue
            normalized[k] = v
        if not normalized:
            raise HTTPException(status_code=400, detail="选项不能为空")
        return dict(sorted(normalized.items()))

    if question_type == "judge":
        true_text = str(options.get("T", "")).strip() or "正确"
        false_text = str(options.get("F", "")).strip() or "错误"
        return {"T": true_text, "F": false_text}

    return options



@router.get("/questions", response_model=List[QuestionOut])
def get_questions(
    skip: int = 0,
    limit: int = 10,
    subject_id: Optional[int] = None,
    question_type: Optional[str] = None,
    important_only: bool = False,
    chapter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Question).filter(Question.deleted_at.is_(None), Question.user_id == current_user.id)
    if subject_id is not None:
        subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == current_user.id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="科目不存在")
        query = query.filter(Question.subject_id == subject_id)
    query = apply_chapter_filter(query, db, current_user, chapter_id)
    if question_type and question_type != "all":
        query = query.filter(Question.type == normalize_question_type(question_type))
    if important_only:
        query = query.filter(Question.is_important == 1)
    return query.order_by(Question.id.asc()).offset(skip).limit(limit).all()


@router.get("/questions/summary")
def get_questions_summary(
    subject_id: Optional[int] = None,
    question_type: Optional[str] = None,
    important_only: bool = False,
    chapter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Question).filter(Question.deleted_at.is_(None), Question.user_id == current_user.id)
    if subject_id is not None:
        subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == current_user.id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="科目不存在")
        query = query.filter(Question.subject_id == subject_id)
    query = apply_chapter_filter(query, db, current_user, chapter_id)
    if question_type and question_type != "all":
        query = query.filter(Question.type == normalize_question_type(question_type))
    if important_only:
        query = query.filter(Question.is_important == 1)

    total = query.count()
    # 只取摘要需要的列，并用 SQLite 的 substr 截断正文，避免把 options / answer /
    # explanation 等大字段整列读回内存
    rows = (
        query.with_entities(
            Question.id,
            func.substr(Question.content, 1, 51).label("content_preview"),
            Question.type,
            Question.is_important,
            Question.subject_id,
            Question.chapter_id,
        )
        .order_by(Question.id.asc())
        .all()
    )

    return {
        "total": total,
        "questions": [
            {
                "id": row.id,
                "content": row.content_preview[:50] + "..." if len(row.content_preview or "") > 50 else (row.content_preview or ""),
                "type": row.type,
                "is_important": row.is_important,
                "subject_id": row.subject_id,
                "chapter_id": row.chapter_id
            }
            for row in rows
        ]
    }


@router.get("/questions/{question_id}/detail")
def get_question_detail(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_user_question(db, current_user.id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return question


@router.patch("/questions/{question_id}/type", response_model=QuestionOut)
def update_question_type(
    question_id: int,
    request: QuestionTypeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_user_question(db, current_user.id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    question.type = normalize_question_type(request.type)
    if question.type == "judge" and not question.options:
        question.options = {"T": "正确", "F": "错误"}
    db.commit()
    db.refresh(question)
    return question


@router.patch("/questions/{question_id}/important", response_model=QuestionOut)
def update_question_important(
    question_id: int,
    request: QuestionImportantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_user_question(db, current_user.id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    question.is_important = 1 if request.is_important else 0
    db.commit()
    db.refresh(question)
    return question


@router.patch("/questions/{question_id}/answer", response_model=QuestionOut)
def update_question_answer(
    question_id: int,
    request: QuestionAnswerUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_user_question(db, current_user.id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    normalized = normalize_standard_answer(question.type, request.answer)
    if not normalized:
        raise HTTPException(status_code=400, detail="答案不能为空")
    question.answer = normalized
    db.commit()
    db.refresh(question)
    return question


@router.patch("/questions/{question_id}/options", response_model=QuestionOut)
def update_question_options(
    question_id: int,
    request: QuestionOptionsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = get_user_question(db, current_user.id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    if question.type not in {"single", "multi", "judge"}:
        raise HTTPException(status_code=400, detail="当前题型不支持修改选项")

    normalized_options = normalize_question_options(question.type, request.options)
    if question.type == "single":
        if not question.answer or question.answer not in normalized_options:
            raise HTTPException(status_code=400, detail="当前答案不在选项中，请先调整答案再修改选项")
    elif question.type == "multi":
        if question.answer:
            if not set(normalize_multi_answer(question.answer)).issubset(set(normalized_options.keys())):
                raise HTTPException(status_code=400, detail="当前答案不在选项中，请先调整答案再修改选项")
    elif question.type == "judge" and question.answer not in {"T", "F"}:
        question.answer = "T"

    question.options = normalized_options
    db.commit()
    db.refresh(question)
    return question


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    question = get_user_question(db, current_user.id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    question.deleted_at = datetime.utcnow()
    db.query(WrongQuestion).filter(WrongQuestion.question_id == question_id, WrongQuestion.user_id == current_user.id).delete()
    db.commit()
    return {"message": "题目已移入垃圾箱"}


@router.post("/questions/batch-delete")
def batch_delete_questions(request: BatchDeleteRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    question_ids = request.question_ids
    if not question_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的题目")

    questions = db.query(Question).filter(Question.id.in_(question_ids), Question.user_id == current_user.id, Question.deleted_at.is_(None)).all()
    if not questions:
        raise HTTPException(status_code=404, detail="题目不存在")

    now = datetime.utcnow()
    for question in questions:
        question.deleted_at = now
    # 一条语句删掉这批题目的错题记录，避免逐题 delete
    db.query(WrongQuestion).filter(
        WrongQuestion.user_id == current_user.id,
        WrongQuestion.question_id.in_([question.id for question in questions]),
    ).delete(synchronize_session=False)
    db.commit()
    return {"message": "题目已批量移入垃圾箱", "count": len(questions)}


@router.post("/practice/submit", response_model=SubmitResponse)
def submit_practice(request: SubmitRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    question = get_user_question(db, current_user.id, request.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    if question.type == "fill" and request.self_evaluation is None:
        return {
            "is_correct": False,
            "correct_answer": question.answer,
            "explanation": question.explanation,
            "removed_from_wrong": False,
            "remaining_to_remove": 0,
            "self_evaluation_required": True,
            "evaluated": False,
        }

    is_correct = request.self_evaluation if question.type == "fill" else is_answer_correct(question.type, request.user_answer, question.answer)
    practice_record = PracticeRecord(
        user_id=current_user.id,
        question_id=request.question_id,
        user_answer=request.user_answer,
        is_correct=1 if is_correct else 0,
    )
    db.add(practice_record)

    threshold = get_wrong_question_threshold()
    removed_from_wrong, remaining_to_remove = update_wrong_question_state(
        db, current_user.id, request.question_id, is_correct, threshold,
    )

    db.commit()
    return {
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
        "removed_from_wrong": removed_from_wrong,
        "remaining_to_remove": remaining_to_remove,
        "self_evaluation_required": False,
        "evaluated": True,
    }


@router.post("/practice/batch-submit")
def batch_submit_practice(request: BatchSubmitRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    threshold = get_wrong_question_threshold()
    results = []
    
    question_ids = [s.question_id for s in request.submissions]
    unique_question_ids = list(set(question_ids))
    
    questions = db.query(Question).filter(
        Question.id.in_(unique_question_ids),
        Question.user_id == current_user.id,
        Question.deleted_at.is_(None)
    ).all()
    question_map = {q.id: q for q in questions}
    wrong_map = {
        wrong.question_id: wrong
        for wrong in db.query(WrongQuestion).filter(
            WrongQuestion.user_id == current_user.id,
            WrongQuestion.question_id.in_(unique_question_ids),
        ).all()
    } if unique_question_ids else {}
    
    for submission in request.submissions:
        question = question_map.get(submission.question_id)
        if not question:
            results.append({
                "question_id": submission.question_id,
                "error": "题目不存在"
            })
            continue
            
        if question.type == "fill" and submission.self_evaluation is None:
            results.append({
                "question_id": submission.question_id,
                "is_correct": False,
                "correct_answer": question.answer,
                "explanation": question.explanation,
                "removed_from_wrong": False,
                "remaining_to_remove": 0,
                "self_evaluation_required": True,
                "evaluated": False,
            })
            continue
            
        is_correct = submission.self_evaluation if question.type == "fill" else is_answer_correct(question.type, submission.user_answer, question.answer)
        practice_record = PracticeRecord(
            user_id=current_user.id,
            question_id=submission.question_id,
            user_answer=submission.user_answer,
            is_correct=1 if is_correct else 0,
        )
        db.add(practice_record)
        
        removed_from_wrong, remaining_to_remove = update_wrong_question_state(
            db,
            current_user.id,
            submission.question_id,
            is_correct,
            threshold,
            wrong_question=wrong_map.get(submission.question_id),
        )
        
        results.append({
            "question_id": submission.question_id,
            "is_correct": is_correct,
            "correct_answer": question.answer,
            "explanation": question.explanation,
            "removed_from_wrong": removed_from_wrong,
            "remaining_to_remove": remaining_to_remove,
            "self_evaluation_required": False,
            "evaluated": True,
        })
    
    db.commit()
    return {"results": results}
