"""题目识别统一流水线：规则优先，AI 只补残块，并缓存补全结果。"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from collections import Counter
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import AiParseCache
from utils.ai_import import complete_residuals_with_ai
from utils.answer_normalizer import normalize_question_type, normalize_standard_answer
from utils.content_hash import normalize_content
from utils.file_extract import clean_extracted_text, is_supported_file
from utils.parser import parse_exercise_text_detailed, parse_file_detailed

logger = logging.getLogger(__name__)

SMART_PARSE_MIN_COVERAGE = float(os.getenv("SMART_PARSE_MIN_COVERAGE", "0.85"))
RESIDUAL_CHUNK_CHARS = int(os.getenv("SMART_PARSE_RESIDUAL_CHARS", "6000"))
MAX_RESIDUAL_REQUESTS = 4
PARSER_VERSION = "1"
PROMPT_VERSION = "1"
CACHE_KIND = "residual_completion"


class QuestionPayload(BaseModel):
    type: str = "single"
    content: str
    options: dict[str, Any] = Field(default_factory=dict)
    answer: str = ""
    explanation: str = ""
    chapter_name: Optional[str] = None
    source: str = "rule"


class ResidualPayload(BaseModel):
    reason: str
    text: str
    chapter_name: str = ""
    index: int = 0
    order: int = 0


class ParseStats(BaseModel):
    question_markers: int = 0
    parsed_count: int = 0
    rule_count: int = 0
    residual_count: int = 0
    remaining_residual_count: int = 0
    coverage: float = 0.0
    ai_used: bool = False
    ai_added: int = 0
    ai_added_questions: int = 0
    cache_hit: bool = False
    estimated_ai_questions: int = 0
    unattributed_lines: int = 0
    source: str = "text"


class SmartParseResult(BaseModel):
    questions: list[QuestionPayload] = Field(default_factory=list)
    residuals: list[ResidualPayload] = Field(default_factory=list)
    stats: ParseStats
    errors: list[str] = Field(default_factory=list)


def _question_payload(
    question: dict[str, Any] | QuestionPayload,
    *,
    chapter_name: Optional[str] = None,
    source: Optional[str] = None,
) -> QuestionPayload:
    if isinstance(question, QuestionPayload):
        return question
    question_type = normalize_question_type(question.get("type", "single"))
    options = {
        str(key).upper(): str(value).strip()
        for key, value in (question.get("options") or {}).items()
        if str(value).strip()
    }
    if question_type == "judge":
        options = {"T": "正确", "F": "错误"}
    return QuestionPayload(
        type=question_type,
        content=str(question.get("content", "")).strip(),
        options=options,
        answer=normalize_standard_answer(question_type, str(question.get("answer", "")).strip()),
        explanation=str(question.get("explanation", "")).strip(),
        chapter_name=chapter_name or question.get("chapter_name") or None,
        source=source or question.get("source") or "rule",
    )


def _empty_stats(source: str = "text") -> ParseStats:
    return ParseStats(source=source)


def _build_stats(
    *,
    questions: list[QuestionPayload],
    residuals: list[dict[str, Any]],
    remaining_residuals: list[dict[str, Any]],
    rule_count: int,
    base_stats: dict[str, Any],
    ai_used: bool,
    ai_added: int,
    cache_hit: bool,
) -> ParseStats:
    question_markers = int(base_stats.get("question_markers") or rule_count + len(residuals))
    coverage = base_stats.get("coverage")
    if coverage is None:
        coverage = rule_count / question_markers if question_markers else 0.0
    estimated_ai_questions = sum(
        max(1, (len(item.get("text", "")) + 499) // 500)
        for item in remaining_residuals
    )
    return ParseStats(
        question_markers=question_markers,
        parsed_count=len(questions),
        rule_count=rule_count,
        residual_count=len(residuals),
        remaining_residual_count=len(remaining_residuals),
        coverage=round(float(coverage), 4),
        ai_used=ai_used,
        ai_added=ai_added,
        ai_added_questions=ai_added,
        cache_hit=cache_hit,
        estimated_ai_questions=estimated_ai_questions,
        unattributed_lines=int(base_stats.get("unattributed_lines") or 0),
        source=str(base_stats.get("source") or "text"),
    )


def _cache_lookup(db: Optional[Session], user_id: Optional[int], text_hash: str) -> Optional[list[dict[str, Any]]]:
    if db is None or user_id is None:
        return None
    try:
        row = (
            db.query(AiParseCache)
            .filter(
                AiParseCache.user_id == user_id,
                AiParseCache.text_hash == text_hash,
                AiParseCache.kind == CACHE_KIND,
            )
            .first()
        )
    except Exception:
        db.rollback()
        return None
    if not row:
        return None
    row.hit_count = (row.hit_count or 0) + 1
    try:
        db.commit()
    except Exception:
        db.rollback()
    payload = row.payload or []
    return payload if isinstance(payload, list) else []


def _cache_store(
    db: Optional[Session],
    user_id: Optional[int],
    text_hash: str,
    blocks: list[dict[str, Any]],
) -> None:
    if db is None or user_id is None:
        return
    try:
        row = (
            db.query(AiParseCache)
            .filter(
                AiParseCache.user_id == user_id,
                AiParseCache.text_hash == text_hash,
                AiParseCache.kind == CACHE_KIND,
            )
            .first()
        )
        if row is None:
            row = AiParseCache(user_id=user_id, text_hash=text_hash, kind=CACHE_KIND)
            db.add(row)
        row.payload = blocks
        row.question_count = sum(len(block.get("questions", [])) for block in blocks)
        db.commit()
    except Exception:
        db.rollback()


def _group_residuals(residuals: list[dict[str, Any]], limit: int) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for residual in residuals:
        size = len(residual.get("text", "")) + 16
        if current and current_chars + size > limit:
            groups.append(current)
            current = []
            current_chars = 0
        current.append(residual)
        current_chars += size
    if current:
        groups.append(current)
    return groups


def _merge_questions(
    rule_questions: list[dict[str, Any]],
    ai_blocks: list[dict[str, Any]],
) -> list[QuestionPayload]:
    items: list[tuple[int, int, dict[str, Any], str, Optional[str]]] = []
    for question in rule_questions:
        order = int(question.get("_order", question.get("order", 0)))
        items.append((order, 0, question, "rule", question.get("chapter_name")))

    for block in ai_blocks:
        order = int(block.get("order", 0))
        chapter_name = block.get("chapter_name") or None
        for index, question in enumerate(block.get("questions", [])):
            items.append((order, index + 1, question, "ai", chapter_name))

    items.sort(key=lambda item: (item[0], item[1]))
    merged: list[QuestionPayload] = []
    seen: set[str] = set()
    for _, _, question, source, chapter_name in items:
        payload = _question_payload(question, chapter_name=chapter_name, source=source)
        if not payload.content:
            continue
        key = normalize_content(payload.content)
        if key in seen:
            continue
        seen.add(key)
        merged.append(payload)
    return merged


async def _complete_parsed(
    parsed: dict[str, Any],
    *,
    api_key: Optional[str],
    db: Optional[Session],
    user_id: Optional[int],
    source_name: Optional[str],
    ai_fallback: bool,
    min_coverage: Optional[float],
) -> SmartParseResult:
    questions = list(parsed.get("questions") or [])
    residuals = list(parsed.get("residuals") or [])
    base_stats = dict(parsed.get("stats") or {})
    errors = list(parsed.get("errors") or [])
    ai_used = False
    ai_added = 0
    cache_hit = False
    ai_blocks: list[dict[str, Any]] = []

    threshold = SMART_PARSE_MIN_COVERAGE if min_coverage is None else min_coverage
    should_try_ai = (
        bool(residuals)
        and ai_fallback
        and bool(api_key)
        and float(base_stats.get("coverage") or 0.0) < threshold
    )

    if should_try_ai:
        ai_used = True
        groups = _group_residuals(residuals, RESIDUAL_CHUNK_CHARS)
        semaphore = asyncio.Semaphore(MAX_RESIDUAL_REQUESTS)

        async def complete_group(group: list[dict[str, Any]]):
            async with semaphore:
                group_text = "\n\n".join(item["text"] for item in group)
                versioned_text = f"{PARSER_VERSION}|{PROMPT_VERSION}|{group_text}"
                text_hash = hashlib.sha256(versioned_text.encode("utf-8")).hexdigest()
                cached = _cache_lookup(db, user_id, text_hash)
                if cached is not None:
                    return cached, [], True

                completed, ai_errors = await complete_residuals_with_ai(
                    [item["text"] for item in group],
                    api_key=api_key,
                    source_name=source_name,
                )
                group_blocks: list[dict[str, Any]] = []
                for item, completed_questions in zip(group, completed):
                    normalized_questions = []
                    for question in completed_questions or []:
                        payload = _question_payload(
                            question,
                            chapter_name=item.get("chapter_name") or None,
                            source="ai",
                        )
                        if payload.content:
                            normalized_questions.append(payload.model_dump())
                    if normalized_questions:
                        group_blocks.append(
                            {
                                "order": item.get("order", 0),
                                "chapter_name": item.get("chapter_name") or "",
                                "questions": normalized_questions,
                            }
                        )
                if group_blocks:
                    _cache_store(db, user_id, text_hash, group_blocks)
                return group_blocks, ai_errors, False

        outcomes = await asyncio.gather(*(complete_group(group) for group in groups))
        for blocks, group_errors, group_cache_hit in outcomes:
            ai_blocks.extend(blocks)
            errors.extend(group_errors)
            cache_hit = cache_hit or group_cache_hit
        ai_added = sum(len(block["questions"]) for block in ai_blocks)

    completed_orders = {int(block.get("order", 0)) for block in ai_blocks}
    remaining_residuals = [
        item for item in residuals
        if int(item.get("order", 0)) not in completed_orders
    ]
    merged = _merge_questions(questions, ai_blocks)
    stats = _build_stats(
        questions=merged,
        residuals=residuals,
        remaining_residuals=remaining_residuals,
        rule_count=len(questions),
        base_stats=base_stats,
        ai_used=ai_used,
        ai_added=ai_added,
        cache_hit=cache_hit,
    )
    reasons = dict(Counter(item.get("reason", "信息不完整") for item in remaining_residuals))
    logger.info(
        "smart_parse coverage=%.3f residuals=%d reasons=%s ai=%d cache_hit=%s source=%s",
        stats.coverage,
        stats.remaining_residual_count,
        reasons,
        stats.ai_added_questions,
        stats.cache_hit,
        stats.source,
    )
    return SmartParseResult(
        questions=merged,
        residuals=remaining_residuals,
        stats=stats,
        errors=errors,
    )


async def smart_parse_text(
    text: str,
    *,
    api_key: Optional[str] = None,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    source_name: Optional[str] = None,
    ai_fallback: bool = True,
    min_coverage: Optional[float] = None,
) -> SmartParseResult:
    cleaned = clean_extracted_text(text or "")
    if not cleaned:
        return SmartParseResult(stats=_empty_stats(), errors=["未提取到有效文本内容"])
    parsed = parse_exercise_text_detailed(cleaned, default_type="single")
    parsed["stats"]["source"] = "text"
    return await _complete_parsed(
        parsed,
        api_key=api_key,
        db=db,
        user_id=user_id,
        source_name=source_name,
        ai_fallback=ai_fallback,
        min_coverage=min_coverage,
    )


async def smart_parse_file(
    filename: str,
    file_bytes: bytes,
    *,
    api_key: Optional[str] = None,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    ai_fallback: bool = True,
    min_coverage: Optional[float] = None,
) -> SmartParseResult:
    if not is_supported_file(filename) or filename.lower().endswith(".zip"):
        return SmartParseResult(
            stats=_empty_stats(),
            errors=[f"不支持的文件格式: {filename}"],
        )
    parsed = parse_file_detailed(file_bytes, filename)
    return await _complete_parsed(
        parsed,
        api_key=api_key,
        db=db,
        user_id=user_id,
        source_name=filename,
        ai_fallback=ai_fallback,
        min_coverage=min_coverage,
    )
