from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import PracticeRecord, Question, Subject, WrongQuestion

router = APIRouter()


class SubjectCreateRequest(BaseModel):
    name: str


class SubjectOut(BaseModel):
    id: int
    name: str
    question_count: int = 0
    wrong_count: int = 0
    created_at: datetime


def normalize_subject_name(name: str) -> str:
    return " ".join(name.strip().split())


def get_or_create_default_subject(db: Session) -> Subject:
    subject = db.query(Subject).filter(Subject.name == "未分类").first()
    if subject:
        return subject

    subject = Subject(name="未分类")
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("/subjects", response_model=List[SubjectOut])
def get_subjects(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Subject,
            func.count(func.distinct(Question.id)).label("question_count"),
            func.count(func.distinct(WrongQuestion.id)).label("wrong_count"),
        )
        .outerjoin(Question, (Question.subject_id == Subject.id) & (Question.deleted_at.is_(None)))
        .outerjoin(WrongQuestion, WrongQuestion.question_id == Question.id)
        .group_by(Subject.id)
        .order_by(Subject.created_at.asc(), Subject.id.asc())
        .all()
    )

    return [
        {
            "id": subject.id,
            "name": subject.name,
            "question_count": question_count,
            "wrong_count": wrong_count,
            "created_at": subject.created_at,
        }
        for subject, question_count, wrong_count in rows
    ]


@router.post("/subjects", response_model=SubjectOut)
def create_subject(request: SubjectCreateRequest, db: Session = Depends(get_db)):
    name = normalize_subject_name(request.name)
    if not name:
        raise HTTPException(status_code=400, detail="科目名称不能为空")

    existing = db.query(Subject).filter(func.lower(Subject.name) == name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="科目已存在")

    subject = Subject(name=name)
    db.add(subject)
    db.commit()
    db.refresh(subject)

    return {
        "id": subject.id,
        "name": subject.name,
        "question_count": 0,
        "wrong_count": 0,
        "created_at": subject.created_at,
    }


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    if subject.name == "未分类":
        raise HTTPException(status_code=400, detail="默认科目不能删除")

    question_ids = [
        question_id
        for (question_id,) in db.query(Question.id).filter(Question.subject_id == subject_id).all()
    ]
    if question_ids:
        db.query(PracticeRecord).filter(PracticeRecord.question_id.in_(question_ids)).delete(synchronize_session=False)
        db.query(WrongQuestion).filter(WrongQuestion.question_id.in_(question_ids)).delete(synchronize_session=False)
        db.query(Question).filter(Question.id.in_(question_ids)).delete(synchronize_session=False)

    db.delete(subject)
    db.commit()
    return {"message": "科目已删除"}
