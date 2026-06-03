from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Question, Subject, User
from routers.subjects import get_or_create_default_subject
from utils.file_extract import extract_text_from_file, save_uploaded_file, extract_zip_file
from utils.parser import parse_exercise_text

router = APIRouter()
UPLOAD_DIR = Path("uploads")
TEXT_EXTRACT_EXTENSIONS = {".txt", ".md"}


class ParsedQuestion(BaseModel):
    type: str = "single"
    content: str
    options: Dict[str, Any] = Field(default_factory=dict)
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


class FileExtractResponse(BaseModel):
    filename: str
    extracted_text: str
    parsed_count: int
    asset_url: str
    asset_ext: str
    asset_saved_name: str
    asset_download_url: str


class SingleFileItem(BaseModel):
    filename: str
    file_type: str  # text, asset
    text_content: str = ""
    parsed_questions: List[ParsedQuestion] = Field(default_factory=list)
    asset_url: str = ""
    asset_download_url: str = ""
    asset_saved_name: str = ""


class MultiFileResponse(BaseModel):
    total_files: int
    processed_files: int
    text_contents: str
    parsed_questions: List[ParsedQuestion]
    assets: List[SingleFileItem]


class QuestionCreateRequest(BaseModel):
    type: str = "single"
    subject_id: Optional[int] = None
    content: str
    options: Dict[str, Any]
    answer: str
    explanation: Optional[str] = ""


class QuestionCreateResponse(BaseModel):
    id: int
    message: str


def normalize_content(content: str) -> str:
    return "".join(content.lower().split())


def normalize_question_type(question_type: str) -> str:
    return question_type if question_type in {"single", "multi", "judge", "fill", "short", "code"} else "single"


def resolve_subject_id(subject_id: Optional[int], db: Session, current_user: User) -> int:
    if subject_id is None:
        return get_or_create_default_subject(db, current_user.id).id
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == current_user.id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    return subject.id


@router.post("/questions", response_model=QuestionCreateResponse)
def create_question(
    request: QuestionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject_id = resolve_subject_id(request.subject_id, db, current_user)
    normalized_content = normalize_content(request.content)
    all_questions = db.query(Question).filter(Question.user_id == current_user.id, Question.subject_id == subject_id, Question.deleted_at.is_(None)).all()
    for q in all_questions:
        if normalize_content(q.content) == normalized_content:
            raise HTTPException(status_code=400, detail="题目已存在")

    new_question = Question(
        user_id=current_user.id,
        subject_id=subject_id,
        type=normalize_question_type(request.type),
        content=request.content,
        options=request.options,
        answer=request.answer,
        explanation=request.explanation or "",
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return {"id": new_question.id, "message": "题目添加成功"}


@router.post("/import/parse", response_model=List[ParsedQuestion])
def parse_questions(request: ParseRequest):
    return parse_exercise_text(request.text)


@router.post("/import/extract-file", response_model=FileExtractResponse)
async def extract_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")
    saved_name, suffix = save_uploaded_file(file.filename, file_bytes, UPLOAD_DIR)
    if suffix not in TEXT_EXTRACT_EXTENSIONS:
        return {
            "filename": file.filename,
            "extracted_text": "",
            "parsed_count": 0,
            "asset_url": f"/uploads/{saved_name}",
            "asset_ext": suffix,
            "asset_saved_name": saved_name,
            "asset_download_url": f"/api/uploads/download/{saved_name}?name={quote(file.filename)}",
        }
    text = extract_text_from_file(file.filename, file_bytes)
    parsed = parse_exercise_text(text)
    return {
        "filename": file.filename,
        "extracted_text": text,
        "parsed_count": len(parsed),
        "asset_url": f"/uploads/{saved_name}",
        "asset_ext": suffix,
        "asset_saved_name": saved_name,
        "asset_download_url": f"/api/uploads/download/{saved_name}?name={quote(file.filename)}",
    }


@router.get("/uploads/download/{saved_name}")
def download_uploaded_file(saved_name: str, name: str = Query("file")):
    safe_saved_name = Path(saved_name).name
    file_path = (UPLOAD_DIR / safe_saved_name).resolve()
    base_dir = UPLOAD_DIR.resolve()
    if not str(file_path).startswith(str(base_dir)):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path=file_path, filename=Path(name).name, media_type="application/octet-stream")


def _process_single_file(
    filename: str,
    file_bytes: bytes,
    upload_dir: Path
) -> SingleFileItem:
    """处理单个文件"""
    suffix = Path(filename).suffix.lower()
    saved_name = ""
    asset_url = ""
    asset_download_url = ""
    text_content = ""
    parsed_questions: List[ParsedQuestion] = []
    file_type = "asset"

    if suffix in TEXT_EXTRACT_EXTENSIONS:
        text_content = extract_text_from_file(filename, file_bytes)
        parsed_questions = [ParsedQuestion(**q) for q in parse_exercise_text(text_content)]
        file_type = "text"
    else:
        saved_name, _ = save_uploaded_file(filename, file_bytes, upload_dir)
        asset_url = f"/uploads/{saved_name}"
        asset_download_url = f"/api/uploads/download/{saved_name}?name={quote(filename)}"
        file_type = "asset"

    return SingleFileItem(
        filename=filename,
        file_type=file_type,
        text_content=text_content,
        parsed_questions=parsed_questions,
        asset_url=asset_url,
        asset_download_url=asset_download_url,
        asset_saved_name=saved_name,
    )


@router.post("/import/extract-multiple", response_model=MultiFileResponse)
async def extract_multiple_files(files: List[UploadFile] = File(...)):
    total_files = 0
    processed_files = 0
    all_text_contents = []
    all_parsed_questions: List[ParsedQuestion] = []
    all_assets: List[SingleFileItem] = []

    for file in files:
        if not file.filename:
            continue
        total_files += 1
        try:
            file_bytes = await file.read()
            if not file_bytes:
                continue

            suffix = Path(file.filename).suffix.lower()

            if suffix == ".zip":
                zip_items = extract_zip_file(file_bytes, UPLOAD_DIR)
                for item in zip_items:
                    processed_item = _process_single_file(
                        item['filename'],
                        item['file_bytes'],
                        UPLOAD_DIR
                    )
                    if processed_item.text_content:
                        all_text_contents.append(f"---\n{processed_item.filename}\n---\n{processed_item.text_content}\n")
                        all_parsed_questions.extend(processed_item.parsed_questions)
                    if processed_item.file_type == "asset":
                        all_assets.append(processed_item)
                    processed_files += 1
            else:
                processed_item = _process_single_file(file.filename, file_bytes, UPLOAD_DIR)
                if processed_item.text_content:
                    all_text_contents.append(f"---\n{processed_item.filename}\n---\n{processed_item.text_content}\n")
                    all_parsed_questions.extend(processed_item.parsed_questions)
                if processed_item.file_type == "asset":
                    all_assets.append(processed_item)
                processed_files += 1
        except Exception:
            continue

    return {
        "total_files": total_files,
        "processed_files": processed_files,
        "text_contents": "\n".join(all_text_contents),
        "parsed_questions": all_parsed_questions,
        "assets": all_assets,
    }


@router.post("/import", response_model=ImportResponse)
def import_questions(
    request: ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject_id = resolve_subject_id(request.subject_id, db, current_user)
    parsed_questions = [q.model_dump() for q in request.questions] if request.questions is not None else parse_exercise_text(request.text)
    parsed_count = len(parsed_questions)
    inserted_count = 0

    known_contents = {
        normalize_content(question.content)
        for question in db.query(Question).filter(
            Question.user_id == current_user.id,
            Question.subject_id == subject_id,
            Question.deleted_at.is_(None),
        ).all()
    }

    for q in parsed_questions:
        normalized_content = normalize_content(q["content"])
        if normalized_content in known_contents:
            continue
        db.add(
            Question(
                user_id=current_user.id,
                subject_id=subject_id,
                type=normalize_question_type(q.get("type", "single")),
                content=q["content"],
                options=q["options"],
                answer=q["answer"],
                explanation=q.get("explanation", ""),
            )
        )
        inserted_count += 1
        known_contents.add(normalized_content)

    db.commit()
    return {"parsed_count": parsed_count, "inserted_count": inserted_count}
