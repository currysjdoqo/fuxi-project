import re
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import unquote

import pytest
from docx import Document
from docx.oxml.ns import qn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import get_current_user
from database import Base, get_db
from models import Chapter, Subject, User
from routers.export import router as export_router


@pytest.fixture()
def export_env():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_local()
    owner = User(username="owner", password_hash="hash")
    other = User(username="other", password_hash="hash")
    db.add_all([owner, other])
    db.flush()
    math = Subject(user_id=owner.id, name="高等数学")
    physics = Subject(user_id=owner.id, name="大学物理")
    other_subject = Subject(user_id=other.id, name="其他科目")
    db.add_all([math, physics, other_subject])
    db.flush()
    first = Chapter(
        user_id=owner.id,
        subject_id=math.id,
        name="第一章 极限",
        summary_md=(
            "# 核心概念\n\n**定义**：极限与连续。\n\n"
            "- 项目一\n1. 第一项\n\n特殊符号：<A&B>"
        ),
        outline_json=[{
            "title": "基础",
            "children": [{"title": "极限", "children": [{"title": "运算法则"}]}],
        }],
    )
    second = Chapter(
        user_id=owner.id,
        subject_id=math.id,
        name="第二章 导数",
        summary_md="## 求导法则\n\n第二章 **重点**",
        outline_json=[{"title": "导数", "children": [{"title": "链式法则"}]}],
    )
    empty = Chapter(user_id=owner.id, subject_id=math.id, name="第三章 积分")
    control = Chapter(
        user_id=owner.id,
        subject_id=math.id,
        name="第四章 控制字符\x0b测试",
        summary_md="# 标题\x00\n\n正文\x0c换页 **加粗\x01**\n- 列表\x1f项",
        outline_json=[{"title": "大纲\x00节点", "children": [{"title": "子节点\x0c"}]}],
    )
    cross_subject = Chapter(user_id=owner.id, subject_id=physics.id, name="其他科目章节")
    other_chapter = Chapter(user_id=other.id, subject_id=other_subject.id, name="无权章节")
    db.add_all([first, second, empty, control, cross_subject, other_chapter])
    db.commit()
    ids = SimpleNamespace(
        first=first.id,
        second=second.id,
        empty=empty.id,
        control=control.id,
        cross_subject=cross_subject.id,
        other=other_chapter.id,
    )

    app = FastAPI()
    app.include_router(export_router, prefix="/api")

    def override_db():
        session = session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: owner
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, ids=ids, engine=engine)
    db.close()
    engine.dispose()


def _post(env, chapter_ids, file_format="md", filename=None):
    return env.client.post(
        "/api/export/chapters",
        json={"chapter_ids": chapter_ids, "format": file_format, "filename": filename},
    )


def _download_filename(response):
    disposition = response.headers["content-disposition"]
    assert re.search(r'filename="[A-Za-z0-9_.-]+"', disposition)
    return unquote(disposition.split("filename*=UTF-8''", 1)[1])


def test_markdown_preserves_order_headings_outline_and_placeholders(export_env):
    ids = export_env.ids
    response = _post(
        export_env,
        [ids.second, ids.first, ids.empty],
        filename="数学复习.md",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert _download_filename(response) == "数学复习.md"
    text = response.content.decode("utf-8")
    assert text.index("# 第二章 导数") < text.index("# 第一章 极限") < text.index("# 第三章 积分")
    assert text.count("\n---\n") == 2
    assert "#### 求导法则" in text
    assert "### 核心概念" in text
    assert "**定义**：极限与连续。" in text
    assert "  - 极限" in text
    assert "    - 运算法则" in text
    assert text.count("尚未生成") == 2


def test_docx_contains_chinese_bold_headings_and_outline_levels(export_env):
    ids = export_env.ids
    response = _post(export_env, [ids.second, ids.first, ids.empty], "docx")

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert _download_filename(response) == "高等数学-章节复习.docx"
    document = Document(BytesIO(response.content))
    paragraphs = document.paragraphs
    texts = [paragraph.text for paragraph in paragraphs]
    assert texts.index("第二章 导数") < texts.index("第一章 极限") < texts.index("第三章 积分")
    assert texts.count("尚未生成") == 2
    bold_texts = [run.text for paragraph in paragraphs for run in paragraph.runs if run.bold]
    assert "定义" in bold_texts
    assert "重点" in bold_texts
    assert next(p for p in paragraphs if p.text == "第一章 极限").style.name == "Heading 1"
    assert next(p for p in paragraphs if p.text == "核心概念").style.name == "Heading 3"
    outline_root = next(p for p in paragraphs if p.text == "基础")
    outline_child = next(p for p in paragraphs if p.text == "极限")
    assert outline_child.paragraph_format.left_indent > outline_root.paragraph_format.left_indent
    normal_fonts = document.styles["Normal"].element.rPr.rFonts
    assert normal_fonts.get(qn("w:eastAsia")) == "宋体"


def test_pdf_is_readable_escaped_and_ordered_with_page_breaks(export_env):
    ids = export_env.ids
    response = _post(export_env, [ids.second, ids.first, ids.empty], "pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert _download_filename(response) == "高等数学-章节复习.pdf"
    reader = PdfReader(BytesIO(response.content))
    assert len(reader.pages) >= 3
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert text.index("第二章 导数") < text.index("第一章 极限") < text.index("第三章 积分")
    assert "特殊符号：<A&B>" in text
    assert "运算法则" in text
    assert "尚未生成" in text


def test_export_strips_control_characters_in_every_format(export_env):
    """控制字符曾让 docx 导出直接 500（XML 不允许 0x00-0x08/0x0B/0x0C/0x0E-0x1F）。"""
    chapter_id = export_env.ids.control
    control_chars = set("\x00\x01\x0b\x0c\x1f")

    markdown = _post(export_env, [chapter_id], "md")
    assert markdown.status_code == 200
    text = markdown.content.decode("utf-8")
    assert not control_chars & set(text)
    assert "第四章 控制字符测试" in text
    assert "加粗" in text
    assert "大纲节点" in text

    docx_response = _post(export_env, [chapter_id], "docx")
    assert docx_response.status_code == 200
    document = Document(BytesIO(docx_response.content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    assert not any(control_chars & set(value) for value in paragraphs)
    assert "第四章 控制字符测试" in paragraphs
    assert "正文换页 加粗" in paragraphs

    pdf_response = _post(export_env, [chapter_id], "pdf")
    assert pdf_response.status_code == 200
    pdf_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf_response.content)).pages)
    assert not control_chars & set(pdf_text)
    assert "第四章 控制字符测试" in pdf_text
    assert "子节点" in pdf_text


def test_filename_is_sanitized_limited_and_has_ascii_fallback(export_env):
    response = _post(
        export_env,
        [export_env.ids.first],
        "md",
        "  ../中文\\复习.pdf.md\u0000  ",
    )
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert 'filename="chapter-review.md"' in disposition
    assert _download_filename(response) == "中文复习.md"

    long_name = _download_filename(_post(export_env, [export_env.ids.first], "md", "长" * 150 + ".md"))
    assert len(long_name.removesuffix(".md")) == 100
    assert _download_filename(_post(export_env, [export_env.ids.first], "md", "...")) == "第一章 极限.md"


def test_export_rejects_invalid_parameters_permissions_and_cross_subject(export_env):
    ids = export_env.ids
    assert _post(export_env, []).status_code == 400
    assert _post(export_env, [ids.first, ids.first]).status_code == 400
    assert _post(export_env, [ids.first], "txt").status_code == 422
    assert _post(export_env, [999999]).status_code == 404
    assert _post(export_env, [ids.other]).status_code == 404
    assert _post(export_env, [ids.first, ids.cross_subject]).status_code == 400


def test_export_reads_only_chapter_and_subject_without_ai_or_temp_files(
    export_env, monkeypatch, tmp_path
):
    from utils import ai_knowledge

    async def unexpected_ai_call(*args, **kwargs):
        raise AssertionError("导出不应调用 AI")

    monkeypatch.setattr(ai_knowledge, "generate_summary_with_ai", unexpected_ai_call)
    monkeypatch.setattr(ai_knowledge, "generate_outline_with_ai", unexpected_ai_call)
    monkeypatch.chdir(tmp_path)
    statements = []

    def record_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(export_env.engine, "before_cursor_execute", record_sql)
    try:
        for file_format in ("md", "docx", "pdf"):
            response = _post(export_env, [export_env.ids.first], file_format)
            assert response.status_code == 200
    finally:
        event.remove(export_env.engine, "before_cursor_execute", record_sql)

    assert any("FROM chapters" in statement for statement in statements)
    assert any("FROM subjects" in statement for statement in statements)
    assert not any("questions" in statement.lower() for statement in statements)
    assert not any(re.match(r"\s*(INSERT|UPDATE|DELETE)", statement, re.I) for statement in statements)
    assert list(tmp_path.iterdir()) == []
