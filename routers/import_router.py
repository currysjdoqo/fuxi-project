from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from database import get_db
from models import Question, Subject
from routers.subjects import get_or_create_default_subject
from utils.parser import parse_exercise_text

router = APIRouter()


class ParsedQuestion(BaseModel):
    type: str = "single"
    content: str
    options: Dict[str, str] = Field(default_factory=dict)
    answer: str
    explanation: Optional[str] = ""


class ImportRequest(BaseModel):
    text: str = ""
    subject_id: Optional[int] = None
    questions: Optional[List[ParsedQuestion]] = None


class ImportResponse(BaseModel):
    parsed_count: int
    inserted_count: int


class ParseRequest(BaseModel):
    text: str


class QuestionCreateRequest(BaseModel):
    type: str = "single"
    subject_id: Optional[int] = None
    content: str
    options: Dict[str, str]
    answer: str
    explanation: Optional[str] = ""


class QuestionCreateResponse(BaseModel):
    id: int
    message: str


def normalize_content(content: str) -> str:
    return ''.join(content.lower().split())


def normalize_question_type(question_type: str) -> str:
    return question_type if question_type in {"single", "multi", "judge", "fill", "short", "code"} else "single"


def resolve_subject_id(subject_id: Optional[int], db: Session) -> int:
    if subject_id is None:
        return get_or_create_default_subject(db).id

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    return subject.id


@router.post("/questions", response_model=QuestionCreateResponse)
def create_question(request: QuestionCreateRequest, db: Session = Depends(get_db)):
    subject_id = resolve_subject_id(request.subject_id, db)
    normalized_content = normalize_content(request.content)

    all_questions = db.query(Question).filter(Question.subject_id == subject_id, Question.deleted_at.is_(None)).all()
    existing_question = None
    for q in all_questions:
        if normalize_content(q.content) == normalized_content:
            existing_question = q
            break

    if existing_question:
        raise HTTPException(status_code=400, detail="题目已存在")

    new_question = Question(
        subject_id=subject_id,
        type=normalize_question_type(request.type),
        content=request.content,
        options=request.options,
        answer=request.answer,
        explanation=request.explanation or ""
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return {
        "id": new_question.id,
        "message": "题目添加成功"
    }


@router.post("/import/parse", response_model=List[ParsedQuestion])
def parse_questions(request: ParseRequest):
    return parse_exercise_text(request.text)


@router.post("/import", response_model=ImportResponse)
def import_questions(request: ImportRequest, db: Session = Depends(get_db)):
    subject_id = resolve_subject_id(request.subject_id, db)
    parsed_questions = [question.model_dump() for question in request.questions] if request.questions is not None else parse_exercise_text(request.text)
    parsed_count = len(parsed_questions)
    inserted_count = 0

    known_contents = {
        normalize_content(question.content)
        for question in db.query(Question).filter(Question.subject_id == subject_id, Question.deleted_at.is_(None)).all()
    }

    for q in parsed_questions:
        normalized_content = normalize_content(q['content'])

        if normalized_content not in known_contents:
            new_question = Question(
                subject_id=subject_id,
                type=normalize_question_type(q.get("type", "single")),
                content=q['content'],
                options=q['options'],
                answer=q['answer'],
                explanation=q.get('explanation', '')
            )
            db.add(new_question)
            inserted_count += 1
            known_contents.add(normalized_content)

    db.commit()

    return {
        "parsed_count": parsed_count,
        "inserted_count": inserted_count
    }
