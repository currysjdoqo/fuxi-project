import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import AiParseCache, Chapter, Subject, User
from routers import import_router
from routers.import_router import ImportRequest, SmartParseRequest, import_questions, smart_parse
from utils import question_pipeline
from utils.question_pipeline import _complete_parsed, smart_parse_file, smart_parse_text


def _fill_question(content: str, answer: str = "答案") -> dict:
    return {
        "type": "fill",
        "content": content,
        "options": {},
        "answer": answer,
        "explanation": "",
    }


def _mostly_complete_text() -> str:
    return "\n".join(
        f"{number}. 第{number}题" + ("" if number == 10 else "\n答案：内容")
        for number in range(1, 11)
    )


def test_one_residual_can_add_three_questions_without_negative_count(monkeypatch) -> None:
    async def fake_complete(blocks, api_key, source_name):
        assert len(blocks) == 1
        return [[_fill_question(f"AI 第{number}题") for number in range(1, 4)]], []

    monkeypatch.setattr(question_pipeline, "complete_residuals_with_ai", fake_complete)
    result = asyncio.run(smart_parse_text("一段没有编号的残缺材料", api_key="test-key"))

    assert result.stats.residual_count == 1
    assert result.stats.remaining_residual_count == 0
    assert result.stats.ai_added_questions == 3
    assert result.stats.parsed_count == 3
    assert result.residuals == []


def test_cache_hit_avoids_ai_and_parser_version_invalidates_old_cache(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AiParseCache.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    calls = 0

    async def fake_complete(blocks, api_key, source_name):
        nonlocal calls
        calls += 1
        return [[_fill_question(blocks[0])]], []

    monkeypatch.setattr(question_pipeline, "complete_residuals_with_ai", fake_complete)
    monkeypatch.setattr(question_pipeline, "PARSER_VERSION", "1")

    def parse():
        return asyncio.run(smart_parse_text(
            "待补全的残块",
            api_key="test-key",
            db=session,
            user_id=1,
            min_coverage=1.0,
        ))

    first = parse()
    second = parse()
    monkeypatch.setattr(question_pipeline, "PARSER_VERSION", "2")
    third = parse()

    assert calls == 2
    assert not first.stats.cache_hit
    assert second.stats.cache_hit
    assert not third.stats.cache_hit
    assert second.questions[0].content == "待补全的残块"
    assert session.query(AiParseCache).count() == 2
    session.close()
    engine.dispose()


def test_force_residuals_route_really_triggers_ai(monkeypatch) -> None:
    calls = 0

    async def fake_complete(blocks, api_key, source_name):
        nonlocal calls
        calls += 1
        return [[_fill_question("AI 补全题")]], []

    monkeypatch.setattr(question_pipeline, "complete_residuals_with_ai", fake_complete)
    monkeypatch.setattr(import_router, "get_user_deepseek_api_key", lambda _user: "test-key")
    user = User(id=1, username="demo", password_hash="hash")

    normal = asyncio.run(smart_parse(
        SmartParseRequest(text=_mostly_complete_text()), current_user=user, db=None
    ))
    assert normal.stats.coverage == 0.9
    assert not normal.stats.ai_used
    assert calls == 0

    forced = asyncio.run(smart_parse(
        SmartParseRequest(text=_mostly_complete_text(), force_residuals=True), current_user=user, db=None
    ))
    assert forced.stats.ai_used
    assert forced.stats.remaining_residual_count == 0
    assert calls == 1


def test_residual_groups_run_concurrently_and_keep_original_order(monkeypatch) -> None:
    active = 0
    max_active = 0

    async def fake_complete(blocks, api_key, source_name):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        active -= 1
        return [[_fill_question(f"补全{blocks[0]}")]], []

    monkeypatch.setattr(question_pipeline, "complete_residuals_with_ai", fake_complete)
    monkeypatch.setattr(question_pipeline, "RESIDUAL_CHUNK_CHARS", 1)
    parsed = {
        "questions": [],
        "residuals": [
            {"reason": "缺少答案", "text": text, "chapter_name": "", "index": index + 1, "order": index}
            for index, text in enumerate(["甲", "乙", "丙"])
        ],
        "stats": {"coverage": 0.0, "question_markers": 3, "source": "text"},
        "errors": [],
    }

    result = asyncio.run(_complete_parsed(
        parsed,
        api_key="test-key",
        db=None,
        user_id=None,
        source_name=None,
        ai_fallback=True,
        min_coverage=1.0,
    ))

    assert max_active == 3
    assert [question.content for question in result.questions] == ["补全甲", "补全乙", "补全丙"]
    assert result.stats.ai_added_questions == 3


def test_smart_file_uses_real_structured_stats() -> None:
    payload = json.dumps([
        {"type": "fill", "content": "完整题", "answer": "内容"},
        {"type": "fill", "content": "缺答案题", "answer": ""},
    ]).encode()

    result = asyncio.run(smart_parse_file("questions.json", payload, ai_fallback=False))

    assert result.stats.parsed_count == 1
    assert result.stats.residual_count == 1
    assert result.stats.remaining_residual_count == 1
    assert result.stats.coverage == 0.5
    assert result.stats.source == "structured"


def test_import_deduplicates_content_and_normalizes_chapter_spaces() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(id=1, username="demo", password_hash="hash")
    subject = Subject(id=1, user_id=1, name="科目")
    session.add_all([user, subject])
    session.commit()

    first_request = ImportRequest(subject_id=subject.id, questions=[{
        "type": "fill",
        "content": "第一题",
        "options": {},
        "answer": "答案",
        "chapter_name": "第一章　基础",
    }])
    first = asyncio.run(import_questions(first_request, db=session, current_user=user))
    duplicate = asyncio.run(import_questions(first_request, db=session, current_user=user))
    second = asyncio.run(import_questions(ImportRequest(subject_id=subject.id, questions=[{
        "type": "fill",
        "content": "第二题",
        "options": {},
        "answer": "答案",
        "chapter_name": "第一章 基础",
    }]), db=session, current_user=user))

    assert first["inserted_count"] == 1
    assert duplicate["inserted_count"] == 0
    assert second["inserted_count"] == 1
    assert session.query(Chapter).filter(Chapter.subject_id == subject.id).count() == 1
    session.close()
    engine.dispose()
