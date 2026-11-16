"""图片 OCR 的语言包探测，以及「缺 chi_sim」这类环境错误不被误导性文案盖掉。"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import get_current_user
from database import Base, get_db
from models import User
from routers import import_router
from utils import file_extract


class _StubPytesseract:
    """只提供 file_extract 用到的那一个属性。"""

    def __init__(self, tesseract_cmd: str = "") -> None:
        self.pytesseract = SimpleNamespace(tesseract_cmd=tesseract_cmd)


def _write_tessdata(directory: Path, langs) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        (directory / f"{lang}.traineddata").write_bytes(b"stub")
    return directory


@pytest.fixture(autouse=True)
def _reset_lang_state(monkeypatch):
    monkeypatch.setattr(file_extract, "_tessdata_dir_cache", None)
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)


# —— 候选目录 ——


def test_candidates_prefer_env_then_engine_tessdata(tmp_path, monkeypatch):
    env_dir = tmp_path / "env-tessdata"
    monkeypatch.setenv("TESSDATA_PREFIX", str(env_dir))
    exe = tmp_path / "bin" / "tesseract.exe"

    candidates = file_extract._tessdata_candidates(_StubPytesseract(str(exe)))

    assert candidates[0] == env_dir
    assert candidates[1] == tmp_path / "bin" / "tessdata"
    assert file_extract._LOCAL_TESSDATA_DIRS[0] in candidates


def test_candidates_are_deduplicated(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    monkeypatch.setenv("TESSDATA_PREFIX", str(shared))
    # 引擎目录与项目目录都不指向 shared，不会重复；这里验证大小写/重复路径只留一份。
    candidates = file_extract._tessdata_candidates(_StubPytesseract(str(tmp_path / "tesseract.exe")))
    keys = [str(path).lower() for path in candidates]

    assert len(keys) == len(set(keys))


# —— ensure_ocr_languages ——


def test_ensure_ocr_languages_points_tessdata_prefix_at_complete_dir(tmp_path, monkeypatch):
    incomplete = _write_tessdata(tmp_path / "engine", ("eng", "osd"))
    complete = _write_tessdata(tmp_path / "project", ("chi_sim", "eng"))
    monkeypatch.setattr(file_extract, "_tessdata_candidates", lambda module: [incomplete, complete])

    resolved = file_extract.ensure_ocr_languages(_StubPytesseract())

    assert resolved == complete
    # 语言包装在项目目录里时，必须把引擎的 TESSDATA_PREFIX 指过去，否则它继续只用 eng。
    assert file_extract.os.environ["TESSDATA_PREFIX"] == str(complete)


def test_ensure_ocr_languages_caches_resolved_dir(tmp_path, monkeypatch):
    complete = _write_tessdata(tmp_path / "project", ("chi_sim", "eng"))
    monkeypatch.setattr(file_extract, "_tessdata_candidates", lambda module: [complete])
    assert file_extract.ensure_ocr_languages(_StubPytesseract()) == complete

    def _should_not_rescan(module):
        raise AssertionError("缓存命中时不应再扫描目录")

    monkeypatch.setattr(file_extract, "_tessdata_candidates", _should_not_rescan)
    assert file_extract.ensure_ocr_languages(_StubPytesseract()) == complete


def test_missing_chinese_pack_raises_actionable_error(tmp_path, monkeypatch):
    incomplete = _write_tessdata(tmp_path / "engine", ("eng", "osd"))
    monkeypatch.setattr(file_extract, "_tessdata_candidates", lambda module: [incomplete])
    exe = incomplete / "tesseract.exe"

    with pytest.raises(HTTPException) as excinfo:
        file_extract.ensure_ocr_languages(_StubPytesseract(str(exe)))

    assert excinfo.value.status_code == 500
    detail = excinfo.value.detail
    assert "chi_sim" in detail
    assert "缺 chi_sim" in detail  # 指出缺的是哪个语言包
    assert str(incomplete) in detail  # 列出已检查的目录
    assert "TESSDATA_PREFIX" not in file_extract.os.environ


def test_extract_from_image_keeps_language_pack_error(monkeypatch):
    def _raise_language_error(module):
        raise HTTPException(status_code=500, detail="图片 OCR 缺少中文语言包 chi_sim")

    monkeypatch.setattr(file_extract, "ensure_ocr_languages", _raise_language_error)
    monkeypatch.setattr(file_extract, "_configure_tesseract_binary", lambda module: None)

    # 图片内容本身无关紧要：语言包检查在任何解码之前。
    with pytest.raises(HTTPException) as excinfo:
        file_extract._extract_from_image(b"not an image")

    assert excinfo.value.status_code == 500
    assert "chi_sim" in excinfo.value.detail


# —— 接口层不要吞掉环境错误 ——


@pytest.fixture()
def import_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_local()
    user = User(username="importer", password_hash="hash")
    db.add(user)
    db.commit()

    app = FastAPI()
    app.include_router(import_router.router, prefix="/api")

    def override_db():
        session = session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client
    db.close()
    engine.dispose()


def _upload_image(client):
    return client.post(
        "/api/import/smart-parse-file",
        files={"file": ("questions.png", b"fake-png-bytes", "image/png")},
    )


def test_ocr_environment_error_is_not_masked_by_api_key_hint(import_client, monkeypatch):
    def _raise_missing_pack(filename, file_bytes):
        raise HTTPException(
            status_code=500,
            detail="图片 OCR 缺少中文语言包 chi_sim，请把 chi_sim.traineddata 放到 data\\tessdata 目录后重试。",
        )

    monkeypatch.setattr(import_router, "extract_text_from_file", _raise_missing_pack)

    response = _upload_image(import_client)

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "chi_sim" in detail
    # 关键回归点：环境问题不该被改写成「请配置 DeepSeek API Key」。
    assert "API Key" not in detail


def test_ocr_failure_without_api_key_keeps_reason_and_hint(import_client, monkeypatch):
    def _raise_undecodable(filename, file_bytes):
        raise HTTPException(status_code=400, detail="图片解析成功，但未识别到文本内容。")

    monkeypatch.setattr(import_router, "extract_text_from_file", _raise_undecodable)

    response = _upload_image(import_client)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "未识别到文本内容" in detail
    assert "DeepSeek API Key" in detail
