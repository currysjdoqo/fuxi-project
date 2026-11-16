import unicodedata
from pathlib import Path
from typing import List, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Chapter, Question, Subject, User
from utils.chapter_exporter import export_chapters as build_chapter_export
from utils.exporter import export_to_pdf, export_to_word, get_supported_types

router = APIRouter(prefix="/export", tags=["导出"])


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
        raise HTTPException(status_code=404, detail="科目不存在")
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
        raise HTTPException(status_code=400, detail="没有可导出的题目")

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


class ChapterExportRequest(BaseModel):
    chapter_ids: List[int]
    format: Literal["pdf", "docx", "md"]
    filename: Optional[str] = None


def _clean_filename_stem(value):
    cleaned = "".join(
        char for char in (value or "")
        if char not in "/\\" and unicodedata.category(char) != "Cc"
    ).strip()
    while cleaned.lower().endswith((".pdf", ".docx", ".md")):
        cleaned = cleaned.rsplit(".", 1)[0].strip()
    return cleaned.strip(" .")[:100].rstrip(" .")


def _chapter_content_disposition(filename):
    stem = Path(filename).stem
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    ascii_stem = "".join(
        char if char.isalnum() or char in ("-", "_") else "-"
        for char in ascii_stem
    ).strip("-._")
    fallback = f"{ascii_stem or 'chapter-review'}{Path(filename).suffix}"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


@router.post("/chapters")
def export_chapter_review(
    request: ChapterExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not request.chapter_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个章节")
    if len(set(request.chapter_ids)) != len(request.chapter_ids):
        raise HTTPException(status_code=400, detail="章节 ID 不能重复")

    rows = db.query(Chapter).filter(
        Chapter.id.in_(request.chapter_ids),
        Chapter.user_id == current_user.id,
    ).all()
    chapters_by_id = {chapter.id: chapter for chapter in rows}
    if len(chapters_by_id) != len(request.chapter_ids):
        raise HTTPException(status_code=404, detail="章节不存在或无权访问")
    chapters = [chapters_by_id[chapter_id] for chapter_id in request.chapter_ids]

    subject_ids = {chapter.subject_id for chapter in chapters}
    if len(subject_ids) != 1:
        raise HTTPException(status_code=400, detail="不能跨科目导出章节")
    subject = db.query(Subject).filter(
        Subject.id == chapters[0].subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在或无权访问")

    default_name = chapters[0].name if len(chapters) == 1 else f"{subject.name}-章节复习"
    stem = _clean_filename_stem(request.filename) or _clean_filename_stem(default_name) or "章节复习"
    extension = f".{request.format}"
    filename = f"{stem}{extension}"
    chapter_data = [
        {
            "name": chapter.name,
            "summary_md": chapter.summary_md,
            "outline_json": chapter.outline_json,
        }
        for chapter in chapters
    ]
    content = build_chapter_export(chapter_data, request.format)
    media_types = {
        "md": "text/markdown; charset=utf-8",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
    }
    return Response(
        content=content,
        media_type=media_types[request.format],
        headers={"Content-Disposition": _chapter_content_disposition(filename)},
    )


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
