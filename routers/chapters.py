from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Chapter, Question, Subject, User, WrongQuestion

router = APIRouter()


class ChapterCreateRequest(BaseModel):
    subject_id: int
    name: str


class ChapterUpdateRequest(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class ChapterBatchMoveRequest(BaseModel):
    # None 或 0 表示移出章节（变为未分章）
    chapter_id: Optional[int] = None
    question_ids: List[int]


class ChapterOut(BaseModel):
    id: int
    subject_id: int
    name: str
    sort_order: int = 0
    question_count: int = 0
    wrong_count: int = 0
    created_at: datetime


def normalize_chapter_name(name: str) -> str:
    return " ".join(name.strip().split())


def get_user_chapter(db: Session, user_id: int, chapter_id: int) -> Optional[Chapter]:
    return db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.user_id == user_id,
    ).first()


def chapter_to_dict(chapter: Chapter, question_count: int = 0, wrong_count: int = 0) -> dict:
    return {
        "id": chapter.id,
        "subject_id": chapter.subject_id,
        "name": chapter.name,
        "sort_order": chapter.sort_order or 0,
        "question_count": question_count,
        "wrong_count": wrong_count,
        "created_at": chapter.created_at,
    }


def get_chapter_counts(db: Session, user_id: int, chapter_id: int) -> tuple[int, int]:
    question_count = db.query(func.count(Question.id)).filter(
        Question.chapter_id == chapter_id,
        Question.user_id == user_id,
        Question.deleted_at.is_(None),
    ).scalar() or 0
    wrong_count = db.query(func.count(func.distinct(WrongQuestion.id))).join(
        Question, Question.id == WrongQuestion.question_id
    ).filter(
        Question.chapter_id == chapter_id,
        WrongQuestion.user_id == user_id,
        Question.deleted_at.is_(None),
    ).scalar() or 0
    return question_count, wrong_count


@router.get("/subjects/{subject_id}/chapters", response_model=List[ChapterOut])
def list_chapters(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    rows = (
        db.query(
            Chapter,
            func.count(func.distinct(Question.id)).label("question_count"),
            func.count(func.distinct(WrongQuestion.id)).label("wrong_count"),
        )
        .outerjoin(
            Question,
            (Question.chapter_id == Chapter.id)
            & (Question.deleted_at.is_(None))
            & (Question.user_id == current_user.id),
        )
        .outerjoin(
            WrongQuestion,
            (WrongQuestion.question_id == Question.id)
            & (WrongQuestion.user_id == current_user.id),
        )
        .filter(Chapter.subject_id == subject_id, Chapter.user_id == current_user.id)
        .group_by(Chapter.id)
        .order_by(Chapter.sort_order.asc(), Chapter.id.asc())
        .all()
    )

    return [
        chapter_to_dict(chapter, question_count, wrong_count)
        for chapter, question_count, wrong_count in rows
    ]


@router.post("/chapters", response_model=ChapterOut)
def create_chapter(
    request: ChapterCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = normalize_chapter_name(request.name)
    if not name:
        raise HTTPException(status_code=400, detail="章节名称不能为空")

    subject = db.query(Subject).filter(
        Subject.id == request.subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    existing = (
        db.query(Chapter)
        .filter(
            Chapter.subject_id == subject.id,
            Chapter.user_id == current_user.id,
            func.lower(Chapter.name) == name.lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="章节已存在")

    max_order = db.query(func.max(Chapter.sort_order)).filter(
        Chapter.subject_id == subject.id,
        Chapter.user_id == current_user.id,
    ).scalar() or 0

    chapter = Chapter(
        user_id=current_user.id,
        subject_id=subject.id,
        name=name,
        sort_order=(max_order or 0) + 1,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter_to_dict(chapter)


@router.patch("/chapters/{chapter_id}", response_model=ChapterOut)
def update_chapter(
    chapter_id: int,
    request: ChapterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chapter = get_user_chapter(db, current_user.id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if request.name is not None:
        name = normalize_chapter_name(request.name)
        if not name:
            raise HTTPException(status_code=400, detail="章节名称不能为空")
        existing = (
            db.query(Chapter)
            .filter(
                Chapter.subject_id == chapter.subject_id,
                Chapter.user_id == current_user.id,
                func.lower(Chapter.name) == name.lower(),
                Chapter.id != chapter.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="章节已存在")
        chapter.name = name

    if request.sort_order is not None:
        chapter.sort_order = request.sort_order

    db.commit()
    db.refresh(chapter)
    question_count, wrong_count = get_chapter_counts(db, current_user.id, chapter.id)
    return chapter_to_dict(chapter, question_count, wrong_count)


@router.delete("/chapters/{chapter_id}")
def delete_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chapter = get_user_chapter(db, current_user.id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 只删章节，不删题：题目退回未分章
    db.query(Question).filter(
        Question.chapter_id == chapter.id,
        Question.user_id == current_user.id,
    ).update({Question.chapter_id: None}, synchronize_session=False)

    db.delete(chapter)
    db.commit()
    return {"message": "章节已删除，章节下题目已移至未分章"}


@router.post("/chapters/batch-move")
def batch_move_questions(
    request: ChapterBatchMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not request.question_ids:
        raise HTTPException(status_code=400, detail="请选择要移动的题目")

    target_chapter = None
    if request.chapter_id:
        target_chapter = get_user_chapter(db, current_user.id, request.chapter_id)
        if not target_chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

    questions = db.query(Question).filter(
        Question.id.in_(request.question_ids),
        Question.user_id == current_user.id,
        Question.deleted_at.is_(None),
    ).all()
    if not questions:
        raise HTTPException(status_code=404, detail="题目不存在")

    if target_chapter:
        for question in questions:
            if question.subject_id != target_chapter.subject_id:
                raise HTTPException(status_code=400, detail="章节与题目不属于同一科目，无法移动")

    target_id = target_chapter.id if target_chapter else None
    for question in questions:
        question.chapter_id = target_id

    db.commit()
    return {
        "message": f"已将 {len(questions)} 道题目移动到「{target_chapter.name if target_chapter else '未分章'}」",
        "count": len(questions),
    }


# ---------- AI 知识点提炼 ----------

def _get_chapter_questions(db: Session, user_id: int, chapter_id: int) -> list[Question]:
    """获取章节下所有未删除题目。"""
    return (
        db.query(Question)
        .filter(
            Question.chapter_id == chapter_id,
            Question.user_id == user_id,
            Question.deleted_at.is_(None),
        )
        .order_by(Question.id.asc())
        .all()
    )


def _question_to_ai_dict(q: Question) -> dict:
    return {
        "content": q.content,
        "type": q.type,
        "answer": q.answer or "",
        "explanation": q.explanation or "",
    }


@router.post("/chapters/{chapter_id}/tag-questions")
async def tag_chapter_questions(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 为本章题目批量打知识点标签。"""
    from utils.ai_access import get_user_deepseek_api_key
    from utils.ai_knowledge import tag_questions_with_ai

    chapter = get_user_chapter(db, current_user.id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        raise HTTPException(status_code=400, detail="请先配置个人 DeepSeek API Key")

    questions = _get_chapter_questions(db, current_user.id, chapter_id)
    if not questions:
        raise HTTPException(status_code=400, detail="该章节没有题目")

    question_dicts = [_question_to_ai_dict(q) for q in questions]
    tags, errors = await tag_questions_with_ai(question_dicts, api_key)

    # 写入题目 knowledge_tags
    tag_map: dict[int, list[str]] = {}
    for item in tags:
        tag_map[item["index"]] = item["tags"]

    tagged_count = 0
    for i, q in enumerate(questions):
        if i in tag_map:
            q.knowledge_tags = tag_map[i]
            tagged_count += 1

    chapter.tags_generated_at = datetime.utcnow()
    db.commit()

    return {
        "message": f"已为 {tagged_count} 道题目打上知识点标签",
        "tagged_count": tagged_count,
        "errors": errors,
    }


@router.post("/chapters/{chapter_id}/generate-summary")
async def generate_chapter_summary(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 生成本章知识点总结（Markdown）。"""
    from utils.ai_access import get_user_deepseek_api_key
    from utils.ai_knowledge import generate_summary_with_ai

    chapter = get_user_chapter(db, current_user.id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        raise HTTPException(status_code=400, detail="请先配置个人 DeepSeek API Key")

    questions = _get_chapter_questions(db, current_user.id, chapter_id)
    if not questions:
        raise HTTPException(status_code=400, detail="该章节没有题目，无法生成总结")

    question_dicts = [_question_to_ai_dict(q) for q in questions]
    summary_md, errors = await generate_summary_with_ai(
        question_dicts, chapter.name, api_key,
    )

    if summary_md:
        chapter.summary_md = summary_md
        chapter.summary_generated_at = datetime.utcnow()
        db.commit()

    return {
        "summary_md": summary_md,
        "errors": errors,
    }


@router.post("/chapters/{chapter_id}/generate-outline")
async def generate_chapter_outline(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 生成本章知识大纲（树形 JSON）。"""
    from utils.ai_access import get_user_deepseek_api_key
    from utils.ai_knowledge import generate_outline_with_ai

    chapter = get_user_chapter(db, current_user.id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        raise HTTPException(status_code=400, detail="请先配置个人 DeepSeek API Key")

    questions = _get_chapter_questions(db, current_user.id, chapter_id)
    if not questions:
        raise HTTPException(status_code=400, detail="该章节没有题目，无法生成大纲")

    question_dicts = [_question_to_ai_dict(q) for q in questions]
    outline, errors = await generate_outline_with_ai(
        question_dicts, chapter.name, api_key,
    )

    if outline:
        chapter.outline_json = outline
        chapter.outline_generated_at = datetime.utcnow()
        db.commit()

    return {
        "outline": outline,
        "errors": errors,
    }


@router.get("/chapters/{chapter_id}/knowledge")
def get_chapter_knowledge(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读取章节的知识点提炼缓存结果。"""
    chapter = get_user_chapter(db, current_user.id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    questions = _get_chapter_questions(db, current_user.id, chapter_id)

    return {
        "chapter_id": chapter.id,
        "chapter_name": chapter.name,
        "summary_md": chapter.summary_md,
        "outline": chapter.outline_json,
        "summary_generated_at": chapter.summary_generated_at,
        "outline_generated_at": chapter.outline_generated_at,
        "tags_generated_at": chapter.tags_generated_at,
        "questions": [
            {
                "id": q.id,
                "content": q.content,
                "type": q.type,
                "answer": q.answer,
                "knowledge_tags": q.knowledge_tags,
            }
            for q in questions
        ],
    }


@router.post("/chapters/{chapter_id}/extract-all")
async def extract_all_knowledge(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """一键提炼本章：依次执行打标签 → 生成总结 → 生成大纲。"""
    from utils.ai_access import get_user_deepseek_api_key
    from utils.ai_knowledge import (
        tag_questions_with_ai,
        generate_summary_with_ai,
        generate_outline_with_ai,
    )

    chapter = get_user_chapter(db, current_user.id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        raise HTTPException(status_code=400, detail="请先配置个人 DeepSeek API Key")

    questions = _get_chapter_questions(db, current_user.id, chapter_id)
    if not questions:
        raise HTTPException(status_code=400, detail="该章节没有题目")

    question_dicts = [_question_to_ai_dict(q) for q in questions]
    all_errors: list[str] = []
    tagged_count = 0

    # 1. 打标签
    tags, errors = await tag_questions_with_ai(question_dicts, api_key)
    all_errors.extend(errors)
    tag_map: dict[int, list[str]] = {item["index"]: item["tags"] for item in tags}
    for i, q in enumerate(questions):
        if i in tag_map:
            q.knowledge_tags = tag_map[i]
            tagged_count += 1
    chapter.tags_generated_at = datetime.utcnow()
    db.commit()

    # 2. 生成总结
    summary_md, errors = await generate_summary_with_ai(
        question_dicts, chapter.name, api_key,
    )
    all_errors.extend(errors)
    if summary_md:
        chapter.summary_md = summary_md
        chapter.summary_generated_at = datetime.utcnow()
        db.commit()

    # 3. 生成大纲
    outline, errors = await generate_outline_with_ai(
        question_dicts, chapter.name, api_key,
    )
    all_errors.extend(errors)
    if outline:
        chapter.outline_json = outline
        chapter.outline_generated_at = datetime.utcnow()
        db.commit()

    return {
        "message": f"提炼完成：标签 {tagged_count} 题，总结 {'已生成' if summary_md else '失败'}，大纲 {'已生成' if outline else '失败'}",
        "tagged_count": tagged_count,
        "has_summary": bool(summary_md),
        "has_outline": bool(outline),
        "errors": all_errors,
    }


# ---------- 存量未分章题目 AI 划分 ----------

class AssignUnassignedRequest(BaseModel):
    subject_id: int


@router.get("/subjects/{subject_id}/unassigned-questions")
def get_unassigned_questions(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某科目下未分章的题目列表。"""
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    questions = (
        db.query(Question)
        .filter(
            Question.subject_id == subject_id,
            Question.user_id == current_user.id,
            Question.chapter_id.is_(None),
            Question.deleted_at.is_(None),
        )
        .order_by(Question.id.asc())
        .all()
    )

    return {
        "count": len(questions),
        "questions": [
            {
                "id": q.id,
                "type": q.type,
                "content": q.content,
                "answer": q.answer or "",
            }
            for q in questions
        ],
    }


@router.post("/subjects/{subject_id}/ai-assign-unassigned")
async def ai_assign_unassigned_questions(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    对某科目下所有未分章的存量题目，调用 AI 划分章节并落库。
    AI 返回章节名后：已有同名章节则匹配，不存在则自动新建。
    """
    from utils.ai_access import get_user_deepseek_api_key
    from utils.ai_chapter_assign import assign_chapters_with_ai

    api_key = get_user_deepseek_api_key(current_user)
    if not api_key:
        raise HTTPException(status_code=400, detail="请先配置个人 DeepSeek API Key")

    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    questions = (
        db.query(Question)
        .filter(
            Question.subject_id == subject_id,
            Question.user_id == current_user.id,
            Question.chapter_id.is_(None),
            Question.deleted_at.is_(None),
        )
        .order_by(Question.id.asc())
        .all()
    )
    if not questions:
        raise HTTPException(status_code=400, detail="该科目没有未分章的题目")

    # 获取已有章节名列表
    existing_chapters = (
        db.query(Chapter)
        .filter(
            Chapter.subject_id == subject_id,
            Chapter.user_id == current_user.id,
        )
        .all()
    )
    existing_names = [ch.name for ch in existing_chapters]

    # 构造 AI 输入（每题只传 content 和 type）
    question_dicts = [
        {"content": q.content, "type": q.type}
        for q in questions
    ]

    assignments, errors = await assign_chapters_with_ai(
        questions=question_dicts,
        existing_chapter_names=existing_names,
        api_key=api_key,
    )

    # 建立 chapter_name → Chapter 的映射（含自动建章）
    chapter_map: dict[str, Chapter] = {}
    for ch in existing_chapters:
        chapter_map[normalize_chapter_name(ch.name)] = ch

    max_order = db.query(func.max(Chapter.sort_order)).filter(
        Chapter.subject_id == subject_id,
        Chapter.user_id == current_user.id,
    ).scalar() or 0

    assigned_count = 0
    for item in assignments:
        idx = item["index"]
        chapter_name = normalize_chapter_name(item["chapter"])
        if not chapter_name or idx >= len(questions):
            continue

        if chapter_name not in chapter_map:
            # 自动建章
            max_order += 1
            new_chapter = Chapter(
                user_id=current_user.id,
                subject_id=subject_id,
                name=chapter_name,
                sort_order=max_order,
            )
            db.add(new_chapter)
            db.flush()
            chapter_map[chapter_name] = new_chapter

        questions[idx].chapter_id = chapter_map[chapter_name].id
        assigned_count += 1

    db.commit()

    # 统计 AI 划分出的章节名
    ai_chapter_names = list(set(
        normalize_chapter_name(item["chapter"])
        for item in assignments
        if normalize_chapter_name(item["chapter"])
    ))
    new_chapter_names = [
        name for name in ai_chapter_names
        if name not in [normalize_chapter_name(ch.name) for ch in existing_chapters]
    ]

    return {
        "message": f"AI 已为 {assigned_count} 道未分章题目划分章节"
                   + (f"，新建章节 {len(new_chapter_names)} 个" if new_chapter_names else ""),
        "assigned_count": assigned_count,
        "total_unassigned": len(questions),
        "new_chapter_names": new_chapter_names,
        "errors": errors,
    }
