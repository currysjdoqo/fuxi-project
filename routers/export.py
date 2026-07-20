from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Question, Subject, User
from utils.exporter import export_to_pdf, export_to_word, get_supported_types

router = APIRouter(prefix="/export", tags=["瀵煎嚭"])


class ExportInfo(BaseModel):
    subject_name: str
    total_questions: int
    supported_types: List[str]
    formats: List[dict]


def _get_owned_subject(db: Session, subject_id: int, current_user: User) -> Subject:
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="绉戠洰涓嶅瓨鍦?")
    return subject


@router.get("/info", response_model=ExportInfo)
def get_export_info(
    subject_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = _get_owned_subject(db, subject_id, current_user)
    total_questions = db.query(Question).filter(
        Question.subject_id == subject_id,
        Question.user_id == current_user.id,
        Question.deleted_at.is_(None),
        Question.type.in_(get_supported_types()),
    ).count()
    return ExportInfo(
        subject_name=subject.name,
        total_questions=total_questions,
        supported_types=get_supported_types(),
        formats=[
            {"value": "word", "label": "Word (.docx)"},
            {"value": "pdf", "label": "PDF (.pdf)"},
        ],
    )


@router.post("/preview")
def preview_export(
    subject_id: int = Query(...),
    format: str = Query("word"),
    include_answer: bool = Query(True),
    include_analysis: bool = Query(True),
    limit: int = Query(5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = _get_owned_subject(db, subject_id, current_user)
    query = db.query(Question).filter(
        Question.subject_id == subject_id,
        Question.user_id == current_user.id,
        Question.deleted_at.is_(None),
        Question.type.in_(get_supported_types()),
    )
    questions = query.limit(limit).all()
    return {
        "subject_name": subject.name,
        "preview_questions": [
            {
                "id": q.id,
                "type": q.type,
                "content": q.content,
                "options": q.options if q.options else {},
                "answer": q.answer if include_answer else "",
                "analysis": q.explanation if include_analysis else "",
            }
            for q in questions
        ],
        "total_count": query.count(),
        "format": format,
    }


@router.get("/download")
def export_questions(
    subject_id: int = Query(...),
    format: str = Query("word"),
    include_answer: bool = Query(True),
    include_analysis: bool = Query(True),
    question_ids: Optional[str] = Query(None),
    question_types: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = _get_owned_subject(db, subject_id, current_user)
    query = db.query(Question).filter(
        Question.subject_id == subject_id,
        Question.user_id == current_user.id,
        Question.deleted_at.is_(None),
        Question.type.in_(get_supported_types()),
    )

    if question_types:
        types = [x.strip() for x in question_types.split(",") if x.strip()]
        if types:
            query = query.filter(Question.type.in_(types))

    if question_ids:
        try:
            selected_ids = [int(x.strip()) for x in question_ids.split(",") if x.strip()]
            if selected_ids:
                query = query.filter(Question.id.in_(selected_ids))
        except ValueError:
            pass

    questions = query.all()
    if not questions:
        raise HTTPException(status_code=400, detail="娌℃湁鍙鍑虹殑棰樼洰")

    question_list = [
        {
            "id": q.id,
            "type": q.type,
            "content": q.content,
            "options": q.options if q.options else {},
            "answer": q.answer if include_answer else "",
            "analysis": q.explanation if include_analysis else "",
        }
        for q in questions
    ]

    safe_subject_name = "".join(c for c in subject.name if c.isalnum() or c in (" ", "-", "_")).strip()
    if format == "pdf":
        filepath = export_to_pdf(question_list, safe_subject_name, include_answer, include_analysis)
        media_type = "application/pdf"
    else:
        filepath = export_to_word(question_list, safe_subject_name, include_answer, include_analysis)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(filepath, media_type=media_type, filename=Path(filepath).name)


@router.get("/formats")
def get_formats():
    return [
        {"value": "word", "label": "Word (.docx)"},
        {"value": "pdf", "label": "PDF (.pdf)"},
    ]


@router.get("/types")
def get_question_types():
    type_info = {
        "single": {"label": "单选题", "has_options": True},
        "multiple": {"label": "多选题", "has_options": True},
        "judge": {"label": "判断题", "has_options": False},
        "fill": {"label": "填空题", "has_options": False},
        "short_answer": {"label": "简答题", "has_options": False},
    }
    return [{"value": key, **value} for key, value in type_info.items()]
