import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Chapter, Question, Subject, User
from routers.subjects import get_or_create_default_subject
from utils.answer_normalizer import normalize_question_type, normalize_standard_answer
from utils.content_hash import content_hash, normalize_content
from utils.ai_access import get_user_deepseek_api_key
from utils.ai_import import parse_image_with_ai
from utils.file_extract import (
    IMAGE_EXTENSIONS,
    TEXT_EXTRACT_EXTENSIONS,
    extract_text_from_file,
    extract_zip_file,
    save_uploaded_file,
)
from utils.import_template import generate_excel_template
from utils.question_pipeline import (
    ParseStats,
    QuestionPayload,
    SmartParseResult,
    smart_parse_file,
    smart_parse_text,
)

router = APIRouter()
UPLOAD_DIR = Path("private_uploads")
# 解析类接口同时跑多少个文件（pypdf/openpyxl/OCR 都是 CPU/IO 密集的同步代码）
PARSE_CONCURRENCY = 4


class ParsedQuestion(BaseModel):
    type: str = "single"
    content: str
    options: Dict[str, Any] = Field(default_factory=dict)
    answer: str
    explanation: Optional[str] = ""
    # 章节：chapter_id 优先；chapter_name 非空时按名匹配，不存在则自动建章
    chapter_id: Optional[int] = None
    chapter_name: Optional[str] = ""


class ImportRequest(BaseModel):
    text: str = ""
    subject_id: Optional[int] = None
    questions: Optional[List[ParsedQuestion]] = None


class ImportResponse(BaseModel):
    parsed_count: int
    inserted_count: int


class ParseRequest(BaseModel):
    text: str


class SmartParseRequest(BaseModel):
    text: str
    source_name: Optional[str] = None
    ai_fallback: bool = True
    force_residuals: bool = False


class AiParseRequest(BaseModel):
    text: str
    source_name: Optional[str] = None


class SmartParseResponse(SmartParseResult):
    filename: Optional[str] = None
    ai_available: bool = False
    fallback_used: bool = False


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
    file_type: str
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


class ParseFileResponse(BaseModel):
    filename: str
    parsed_questions: List[ParsedQuestion]
    errors: List[str]
    fallback_used: bool = False


class AiParseResponse(BaseModel):
    parsed_questions: List[ParsedQuestion]
    errors: List[str]
    fallback_used: bool = True


class BatchParseResponse(BaseModel):
    total_files: int
    success_files: int
    fail_files: int
    all_questions: List[ParsedQuestion]
    all_errors: List[str]


class QuestionCreateRequest(BaseModel):
    type: str = "single"
    subject_id: Optional[int] = None
    content: str
    options: Dict[str, Any]
    answer: str
    explanation: Optional[str] = ""
    chapter_id: Optional[int] = None
    chapter_name: Optional[str] = ""


class QuestionCreateResponse(BaseModel):
    id: int
    message: str



def get_user_upload_dir(user_id: int) -> Path:
    return UPLOAD_DIR / str(user_id)


def build_private_asset_url(saved_name: str) -> str:
    return f"/api/uploads/access/{saved_name}"


def build_private_asset_download_url(saved_name: str, filename: str) -> str:
    return f"/api/uploads/download/{saved_name}?name={quote(filename)}"


def build_download_headers(filename: str) -> Dict[str, str]:
    encoded = quote(filename)
    return {
        "Content-Disposition": f"attachment; filename=import-template.xlsx; filename*=UTF-8''{encoded}"
    }


def resolve_subject_id(subject_id: Optional[int], db: Session, current_user: User) -> int:
    if subject_id is None:
        return get_or_create_default_subject(db, current_user.id).id
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == current_user.id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject.id


def resolve_chapter_id(
    db: Session,
    current_user: User,
    subject_id: int,
    chapter_id: Optional[int],
    chapter_name: Optional[str],
) -> Optional[int]:
    """章节归属解析：chapter_id 优先校验；chapter_name 非空时按名匹配，不存在则自动建章。"""
    if chapter_id:
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.user_id == current_user.id,
        ).first()
        if not chapter or chapter.subject_id != subject_id:
            raise HTTPException(status_code=400, detail="章节不存在或不属于该科目")
        return chapter.id

    name = " ".join((chapter_name or "").strip().split())
    if not name:
        return None

    chapters = db.query(Chapter).filter(
        Chapter.subject_id == subject_id,
        Chapter.user_id == current_user.id,
    ).all()
    normalized_name = normalize_content(name)
    existing = next((chapter for chapter in chapters if normalize_content(chapter.name) == normalized_name), None)
    if existing:
        return existing.id

    max_order = db.query(func.max(Chapter.sort_order)).filter(
        Chapter.subject_id == subject_id,
        Chapter.user_id == current_user.id,
    ).scalar() or 0
    chapter = Chapter(
        user_id=current_user.id,
        subject_id=subject_id,
        name=name,
        sort_order=(max_order or 0) + 1,
    )
    db.add(chapter)
    db.flush()
    return chapter.id


def resolve_user_upload_file(saved_name: str, current_user: User) -> Path:
    safe_saved_name = Path(saved_name).name
    base_dir = get_user_upload_dir(current_user.id).resolve()
    file_path = (base_dir / safe_saved_name).resolve()
    if not str(file_path).startswith(str(base_dir)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return file_path


@router.post("/questions", response_model=QuestionCreateResponse)
def create_question(
    request: QuestionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject_id = resolve_subject_id(request.subject_id, db, current_user)
    question_hash = content_hash(request.content)
    duplicate = (
        db.query(Question.id)
        .filter(
            Question.user_id == current_user.id,
            Question.subject_id == subject_id,
            Question.deleted_at.is_(None),
            Question.content_hash == question_hash,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Question already exists")

    chapter_id = resolve_chapter_id(db, current_user, subject_id, request.chapter_id, request.chapter_name)

    new_question = Question(
        user_id=current_user.id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        type=normalize_question_type(request.type),
        content=request.content,
        options=request.options,
        answer=normalize_standard_answer(request.type, request.answer),
        explanation=request.explanation or "",
        content_hash=question_hash,
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return {"id": new_question.id, "message": "Question created"}


@router.post("/import/parse", response_model=List[ParsedQuestion])
async def parse_questions(request: ParseRequest):
    result = await smart_parse_text(request.text, ai_fallback=False)
    return result.questions


@router.post("/import/ai-parse", response_model=AiParseResponse)
async def ai_parse_questions(
    request: AiParseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        raise HTTPException(status_code=400, detail="Please configure your personal DeepSeek API Key first")
    result = await smart_parse_text(
        request.text,
        api_key=api_key,
        db=db,
        user_id=current_user.id,
        source_name=request.source_name,
        ai_fallback=True,
        min_coverage=1.0,
    )
    return AiParseResponse(
        parsed_questions=result.questions,
        errors=result.errors,
        fallback_used=result.stats.ai_used,
    )


@router.post("/import/ai-parse-file", response_model=ParseFileResponse)
async def ai_parse_uploaded_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await _parse_uploaded_smart(file, True, True, current_user, db)
    return ParseFileResponse(
        filename=result.filename or "",
        parsed_questions=result.questions,
        errors=result.errors,
        fallback_used=result.fallback_used,
    )


@router.post("/import/smart-parse", response_model=SmartParseResponse)
async def smart_parse(
    request: SmartParseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = get_user_deepseek_api_key(current_user)
    result = await smart_parse_text(
        request.text,
        api_key=api_key,
        db=db,
        user_id=current_user.id,
        source_name=request.source_name,
        ai_fallback=request.ai_fallback,
        min_coverage=1.0 if request.force_residuals else None,
    )
    return SmartParseResponse(
        **result.model_dump(),
        ai_available=bool(api_key),
        fallback_used=result.stats.ai_used,
    )


async def _parse_uploaded_smart(
    file: UploadFile,
    ai_fallback: bool,
    force_residuals: bool,
    current_user: User,
    db: Session,
) -> SmartParseResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    api_key = get_user_deepseek_api_key(current_user)
    suffix = Path(file.filename).suffix.lower()
    threshold = 1.0 if force_residuals else None

    if suffix in IMAGE_EXTENSIONS:
        ocr_error: HTTPException | None = None
        try:
            ocr_text = await run_in_threadpool(extract_text_from_file, file.filename, file_bytes)
        except HTTPException as exc:
            ocr_error = exc
            ocr_text = ""
        if ocr_text.strip():
            result = await smart_parse_text(
                ocr_text,
                api_key=api_key,
                db=db,
                user_id=current_user.id,
                source_name=file.filename,
                ai_fallback=ai_fallback,
                min_coverage=threshold,
            )
            result.stats.source = "ocr"
            if result.questions or not api_key:
                return SmartParseResponse(
                    **result.model_dump(),
                    filename=file.filename,
                    ai_available=bool(api_key),
                    fallback_used=result.stats.ai_used,
                )
        if not api_key:
            if ocr_error is not None and ocr_error.status_code >= 500:
                # 服务端环境问题（没装 Tesseract、缺 chi_sim 语言包）：原样透传，
                # 否则用户会照着「配置 API Key」的提示去查一个毫不相关的地方。
                raise HTTPException(
                    status_code=ocr_error.status_code,
                    detail=ocr_error.detail,
                ) from ocr_error
            if ocr_error is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"{ocr_error.detail} 如需用 AI 识别兜底，请配置 DeepSeek API Key。",
                ) from ocr_error
            raise HTTPException(
                status_code=400,
                detail="图片未识别出可用题目，请配置 DeepSeek API Key 后使用 AI 图片识别",
            )
        questions, errors = await parse_image_with_ai(file_bytes, file.filename, api_key=api_key)
        payloads = [QuestionPayload(**question, source="vision") for question in questions]
        stats = ParseStats(
            parsed_count=len(payloads),
            ai_used=True,
            ai_added=len(payloads),
            ai_added_questions=len(payloads),
            source="vision",
        )
        return SmartParseResponse(
            questions=payloads,
            stats=stats,
            errors=errors,
            filename=file.filename,
            ai_available=True,
            fallback_used=True,
        )

    result = await smart_parse_file(
        file.filename,
        file_bytes,
        api_key=api_key,
        db=db,
        user_id=current_user.id,
        ai_fallback=ai_fallback,
        min_coverage=threshold,
    )
    return SmartParseResponse(
        **result.model_dump(),
        filename=file.filename,
        ai_available=bool(api_key),
        fallback_used=result.stats.ai_used,
    )


@router.post("/import/smart-parse-file", response_model=SmartParseResponse)
async def smart_parse_uploaded_file(
    file: UploadFile = File(...),
    ai_fallback: bool = Query(default=True),
    force_residuals: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _parse_uploaded_smart(file, ai_fallback, force_residuals, current_user, db)


@router.post("/import/extract-file", response_model=FileExtractResponse)
async def extract_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    saved_name, suffix = save_uploaded_file(file.filename, file_bytes, get_user_upload_dir(current_user.id))
    if suffix not in TEXT_EXTRACT_EXTENSIONS:
        return {
            "filename": file.filename,
            "extracted_text": "",
            "parsed_count": 0,
            "asset_url": build_private_asset_url(saved_name),
            "asset_ext": suffix,
            "asset_saved_name": saved_name,
            "asset_download_url": build_private_asset_download_url(saved_name, file.filename),
        }

    text = await run_in_threadpool(extract_text_from_file, file.filename, file_bytes)
    parsed = await smart_parse_text(text, ai_fallback=False)
    return {
        "filename": file.filename,
        "extracted_text": text,
        "parsed_count": len(parsed.questions),
        "asset_url": build_private_asset_url(saved_name),
        "asset_ext": suffix,
        "asset_saved_name": saved_name,
        "asset_download_url": build_private_asset_download_url(saved_name, file.filename),
    }


@router.get("/uploads/access/{saved_name}")
def access_uploaded_file(
    saved_name: str,
    current_user: User = Depends(get_current_user),
):
    return FileResponse(path=resolve_user_upload_file(saved_name, current_user))


@router.get("/uploads/download/{saved_name}")
def download_uploaded_file(
    saved_name: str,
    name: str = Query("file"),
    current_user: User = Depends(get_current_user),
):
    file_path = resolve_user_upload_file(saved_name, current_user)
    return FileResponse(path=file_path, filename=Path(name).name, media_type="application/octet-stream")


@router.get("/import/template")
def download_import_template():
    template = generate_excel_template()
    return StreamingResponse(
        iter([template.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=build_download_headers("import-template.xlsx"),
    )


@router.post("/import/parse-file", response_model=ParseFileResponse)
async def parse_uploaded_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    result = await smart_parse_file(file.filename, file_bytes, ai_fallback=False)
    return ParseFileResponse(
        filename=file.filename,
        parsed_questions=result.questions,
        errors=result.errors,
        fallback_used=False,
    )


@router.post("/import/batch-parse", response_model=BatchParseResponse)
async def batch_parse_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    total_files = len(files)
    success_files = 0
    fail_files = 0
    all_questions: List[ParsedQuestion] = []
    all_errors: List[str] = []

    uploads: List[tuple[str, bytes]] = []
    for file in files:
        if not file.filename:
            continue
        uploads.append((file.filename, await file.read()))

    semaphore = asyncio.Semaphore(PARSE_CONCURRENCY)

    async def _parse_one(filename: str, file_bytes: bytes):
        async with semaphore:
            return await smart_parse_file(filename, file_bytes, ai_fallback=False)

    outcomes = await asyncio.gather(
        *(_parse_one(filename, file_bytes) for filename, file_bytes in uploads),
        return_exceptions=True,
    )

    for (filename, file_bytes), outcome in zip(uploads, outcomes):
        if not file_bytes:
            all_errors.append(f"File {filename} is empty")
            fail_files += 1
            continue
        if isinstance(outcome, Exception):
            all_errors.append(f"File {filename} parse failed: {outcome}")
            fail_files += 1
            continue
        result = outcome
        if result.errors:
            all_errors.extend([f"{filename}: {err}" for err in result.errors])
        if result.questions:
            all_questions.extend(result.questions)
            success_files += 1
        else:
            fail_files += 1

    return {
        "total_files": total_files,
        "success_files": success_files,
        "fail_files": fail_files,
        "all_questions": all_questions,
        "all_errors": all_errors,
    }


async def _process_single_file(filename: str, file_bytes: bytes, upload_dir: Path) -> SingleFileItem:
    suffix = Path(filename).suffix.lower()
    saved_name = ""
    asset_url = ""
    asset_download_url = ""
    text_content = ""
    parsed_questions: List[ParsedQuestion] = []
    file_type = "asset"

    if suffix in TEXT_EXTRACT_EXTENSIONS:
        text_content = await run_in_threadpool(extract_text_from_file, filename, file_bytes)
        parsed = await smart_parse_text(text_content, ai_fallback=False)
        parsed_questions = list(parsed.questions)
        file_type = "text"
    else:
        saved_name, _ = save_uploaded_file(filename, file_bytes, upload_dir)
        asset_url = build_private_asset_url(saved_name)
        asset_download_url = build_private_asset_download_url(saved_name, filename)

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
async def extract_multiple_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    total_files = 0
    processed_files = 0
    all_text_contents = []
    all_parsed_questions: List[ParsedQuestion] = []
    all_assets: List[SingleFileItem] = []
    user_upload_dir = get_user_upload_dir(current_user.id)

    uploads: List[tuple[str, bytes]] = []
    for file in files:
        if not file.filename:
            continue
        total_files += 1
        file_bytes = await file.read()
        if not file_bytes:
            continue
        uploads.append((file.filename, file_bytes))

    semaphore = asyncio.Semaphore(PARSE_CONCURRENCY)

    async def _process_one(filename: str, file_bytes: bytes):
        async with semaphore:
            if Path(filename).suffix.lower() == ".zip":
                zip_items = await run_in_threadpool(extract_zip_file, file_bytes, user_upload_dir)
                results = []
                for item in zip_items:
                    results.append(
                        await _process_single_file(
                            item["filename"],
                            item["file_bytes"],
                            user_upload_dir,
                        )
                    )
                return results
            return [await _process_single_file(filename, file_bytes, user_upload_dir)]

    outcomes = await asyncio.gather(
        *(_process_one(filename, file_bytes) for filename, file_bytes in uploads),
        return_exceptions=True,
    )

    for outcome in outcomes:
        if isinstance(outcome, Exception):
            continue
        for processed_item in outcome:
            if processed_item.text_content:
                all_text_contents.append(
                    f"---\n{processed_item.filename}\n---\n{processed_item.text_content}\n"
                )
                all_parsed_questions.extend(processed_item.parsed_questions)
            if processed_item.file_type == "asset":
                all_assets.append(processed_item)
            processed_files += 1

    return {
        "total_files": total_files,
        "processed_files": processed_files,
        "text_contents": "\n".join(all_text_contents),
        "parsed_questions": all_parsed_questions,
        "assets": all_assets,
    }


@router.post("/import", response_model=ImportResponse)
async def import_questions(
    request: ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject_id = resolve_subject_id(request.subject_id, db, current_user)
    if request.questions is not None:
        parsed_questions = [q.model_dump() for q in request.questions]
    else:
        parsed = await smart_parse_text(request.text, ai_fallback=False)
        parsed_questions = [q.model_dump() for q in parsed.questions]
    parsed_count = len(parsed_questions)
    inserted_count = 0

    # 只按哈希查重：一次索引查询，不再把整个题库的正文读进内存
    incoming_hashes = {content_hash(question["content"]) for question in parsed_questions}
    known_hashes = {
        row[0]
        for row in db.query(Question.content_hash)
        .filter(
            Question.user_id == current_user.id,
            Question.subject_id == subject_id,
            Question.deleted_at.is_(None),
            Question.content_hash.in_(incoming_hashes),
        )
        .all()
        if row[0]
    }

    # 预加载科目下章节，按 id / 名称建索引，避免每题都查一次章节表
    chapters = (
        db.query(Chapter)
        .filter(Chapter.subject_id == subject_id, Chapter.user_id == current_user.id)
        .all()
    )
    chapter_by_id = {chapter.id: chapter for chapter in chapters}
    chapter_by_name = {normalize_content(chapter.name): chapter for chapter in chapters}
    next_sort_order = max([chapter.sort_order or 0 for chapter in chapters], default=0)

    for question in parsed_questions:
        normalized_type = normalize_question_type(question.get("type", "single"))
        question_hash = content_hash(question["content"])
        if question_hash in known_hashes:
            continue

        chapter = None
        chapter_id_value = question.get("chapter_id")
        if chapter_id_value:
            chapter = chapter_by_id.get(int(chapter_id_value))
            if not chapter:
                raise HTTPException(status_code=400, detail="章节不存在或不属于该科目")
        else:
            chapter_name = " ".join((question.get("chapter_name") or "").strip().split())
            if chapter_name:
                chapter = chapter_by_name.get(normalize_content(chapter_name))
                if not chapter:
                    next_sort_order += 1
                    chapter = Chapter(
                        user_id=current_user.id,
                        subject_id=subject_id,
                        name=chapter_name,
                        sort_order=next_sort_order,
                    )
                    db.add(chapter)
                    db.flush()
                    chapter_by_id[chapter.id] = chapter
                    chapter_by_name[normalize_content(chapter_name)] = chapter

        db.add(
            Question(
                user_id=current_user.id,
                subject_id=subject_id,
                chapter_id=chapter.id if chapter else None,
                type=normalized_type,
                content=question["content"],
                options=question["options"],
                answer=normalize_standard_answer(normalized_type, question["answer"]),
                explanation=question.get("explanation", ""),
                content_hash=question_hash,
            )
        )
        inserted_count += 1
        known_hashes.add(question_hash)

    db.commit()
    return {"parsed_count": parsed_count, "inserted_count": inserted_count}


class AiAssignChaptersRequest(BaseModel):
    subject_id: int
    questions: List[dict]


@router.post("/import/ai-assign-chapters")
async def ai_assign_chapters(
    request: AiAssignChaptersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    调用 DeepSeek 为预览中的一批题目自动划分章节。
    返回 assignments: [{"index": 0, "chapter": "第1章 绪论"}, ...]
    """
    from utils.ai_access import get_user_deepseek_api_key
    from utils.ai_chapter_assign import assign_chapters_with_ai

    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        raise HTTPException(status_code=400, detail="请先配置个人 DeepSeek API Key")

    if not request.questions:
        raise HTTPException(status_code=400, detail="没有可供划分章节的题目")

    # 校验科目归属
    subject = db.query(Subject).filter(
        Subject.id == request.subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    # 获取已有章节名列表
    existing_chapters = (
        db.query(Chapter)
        .filter(
            Chapter.subject_id == request.subject_id,
            Chapter.user_id == current_user.id,
        )
        .all()
    )
    existing_names = [ch.name for ch in existing_chapters]

    assignments, errors = await assign_chapters_with_ai(
        questions=request.questions,
        existing_chapter_names=existing_names,
        api_key=api_key,
    )

    return {
        "assignments": assignments,
        "errors": errors,
    }
