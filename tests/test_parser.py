import json
import re
import sys
from io import BytesIO
from types import SimpleNamespace

import pytest
from docx import Document
from openpyxl import Workbook
from PIL import Image

from utils import file_extract
from utils.answer_normalizer import JUDGE_FALSE_ALIASES, JUDGE_TRUE_ALIASES, normalize_standard_answer
from utils.import_template import COLUMNS
from utils.parser import parse_exercise_text, parse_exercise_text_detailed, parse_file_detailed, parse_structured_questions


def test_inline_answer_supports_brackets_and_middle_position() -> None:
    questions = parse_exercise_text(
        "1. 【答案：A】第一题选什么？ A. 甲 B. 乙\n"
        "2. 答案：B 第二题选什么？ A. 甲 B. 乙"
    )

    assert [question["answer"] for question in questions] == ["A", "B"]
    assert all("答案" not in question["content"] for question in questions)


def test_standard_answer_removes_user_answer_and_score_suffixes() -> None:
    assert normalize_standard_answer("single", "B 我的答案：A 得分：0") == "B"
    assert normalize_standard_answer("multi", "C,A,C 我的答案：AB") == "AC"


@pytest.mark.parametrize("alias", sorted(JUDGE_TRUE_ALIASES | JUDGE_FALSE_ALIASES))
def test_judge_aliases_match_shared_normalizer_and_option_keys(alias: str) -> None:
    result = parse_exercise_text_detailed(f"判断题\n1. 这是一个判断题\n答案：{alias}")

    assert not result["residuals"]
    question = result["questions"][0]
    assert question["answer"] == normalize_standard_answer("judge", alias)
    assert question["options"] == {"T": "正确", "F": "错误"}
    assert question["answer"] in question["options"]


def test_circled_numbers_and_multiple_questions_on_one_line() -> None:
    circled = parse_exercise_text("①第一题\n答案：甲\n②第二题\n答案：乙\n③第三题\n答案：丙")
    merged = parse_exercise_text("1. 第一题 答案：A 2. 第二题 答案：B 3. 第三题 答案：C")

    assert [question["content"] for question in circled] == ["第一题", "第二题", "第三题"]
    assert len(merged) == 3
    assert [question["answer"] for question in merged] == ["A", "B", "C"]


def test_skipped_question_numbers_are_split_without_cutting_numeric_options() -> None:
    skipped = parse_exercise_text("5. 第五题 答案：A 6. 第六题 答案：B 8. 第八题 答案：C")
    numeric_options = parse_exercise_text("1. 下列说法正确的是 1. 是 2. 否\n答案：A")

    assert len(skipped) == 3
    assert [question["content"] for question in skipped] == ["第五题", "第六题", "第八题"]
    assert len(numeric_options) == 1
    assert "1. 是 2. 否" in numeric_options[0]["content"]


def test_missing_answer_and_missing_content_become_residuals() -> None:
    result = parse_exercise_text_detailed("1.\n答案：A\n2. 有题干但没有答案\n3. 完整题\n答案：内容")

    assert len(result["questions"]) == 1
    assert len(result["residuals"]) == 2
    assert {item["reason"] for item in result["residuals"]} == {"缺少题干", "缺少答案"}


def test_coverage_counts_each_incomplete_question_and_unattributed_text() -> None:
    text = "\n".join(
        f"{number}. 第{number}题" + ("" if number > 8 else "\n答案：内容")
        for number in range(1, 11)
    )
    result = parse_exercise_text_detailed(text)
    unattributed = parse_exercise_text_detailed("没有编号的题干\n另一行正文")

    assert result["stats"]["coverage"] == pytest.approx(0.8)
    assert result["stats"]["residual_count"] == 2
    assert len(unattributed["residuals"]) == 1
    assert unattributed["residuals"][0]["reason"] == "未归属正文"
    assert unattributed["stats"]["unattributed_lines"] == 2


def _excel_with_missing_answer() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([column["name"] for column in COLUMNS])
    sheet.append([column["hint"] for column in COLUMNS])
    values = {
        "type": "single",
        "content": "Excel 缺答案题",
        "option_a": "甲",
        "option_b": "乙",
        "answer": "",
    }
    sheet.append([values.get(column["key"], "") for column in COLUMNS])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("missing.xlsx", _excel_with_missing_answer()),
        ("missing.csv", "type,content,option_a,option_b,answer\nsingle,CSV 缺答案题,甲,乙,".encode()),
        ("missing.json", json.dumps([{"type": "single", "content": "JSON 缺答案题", "options": {"A": "甲", "B": "乙"}, "answer": ""}]).encode()),
    ],
    ids=["excel", "csv", "json"],
)
def test_structured_files_preserve_incomplete_rows_as_residuals(filename: str, payload: bytes) -> None:
    result = parse_file_detailed(payload, filename)

    assert result["questions"] == []
    assert result["stats"]["residual_count"] == 1
    assert result["stats"]["coverage"] == 0
    assert result["stats"]["source"] == "structured"
    assert result["residuals"][0]["reason"] == "缺少答案"


def test_structured_options_support_multiline_and_invalid_type_residual() -> None:
    valid = parse_structured_questions([
        {"type": "single", "content": "选项对位", "options": "A. 甲\nB. 乙", "answer": "B"}
    ])
    invalid = parse_structured_questions([
        {"type": "unknown", "content": "无效题型", "options": {"A": "甲"}, "answer": "A", "_error": "题型无效"}
    ])

    assert valid["questions"][0]["options"] == {"A": "甲", "B": "乙"}
    assert invalid["residuals"][0]["reason"] == "题型无效"


def test_docx_three_column_table_keeps_all_rows_aligned() -> None:
    document = Document()
    table = document.add_table(rows=1, cols=3)
    table.rows[0].cells[0].text = "题干"
    table.rows[0].cells[1].text = "选项"
    table.rows[0].cells[2].text = "答案"
    for number in range(1, 11):
        cells = table.add_row().cells
        cells[0].text = f"第{number}题"
        cells[1].text = f"A. 甲{number}\nB. 乙{number}"
        cells[2].text = "A" if number % 2 else "B"
    output = BytesIO()
    document.save(output)

    result = parse_file_detailed(output.getvalue(), "table.docx")

    assert len(result["questions"]) == 10
    assert not result["residuals"]
    assert result["questions"][0]["options"] == {"A": "甲1", "B": "乙1"}
    assert result["questions"][-1]["answer"] == "B"
    assert result["stats"]["source"] == "docx_table"


def test_pdf_removes_repeated_headers_and_page_numbers(monkeypatch) -> None:
    class FakePage:
        def __init__(self, number: int):
            self.number = number

        def extract_text(self):
            return f"重复页眉\n{self.number}. 第{self.number}题\n答案：内容\n{self.number}"

    class FakeReader:
        def __init__(self, _stream):
            self.pages = [FakePage(1), FakePage(2), FakePage(3)]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakeReader))
    text = file_extract._extract_from_pdf(b"fake-pdf")
    cleaned = file_extract.clean_extracted_text(text)

    assert "重复页眉" not in cleaned
    assert "1. 第1题" in cleaned
    assert "3. 第3题" in cleaned
    assert cleaned.splitlines()[-1] == "答案：内容"
    assert text.source == "text"


def test_scanned_pdf_falls_back_to_embedded_image_ocr(monkeypatch) -> None:
    class FakePage:
        images = [SimpleNamespace(data=b"embedded-image")]

        @staticmethod
        def extract_text():
            return ""

    class FakeReader:
        def __init__(self, _stream):
            self.pages = [FakePage()]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakeReader))
    monkeypatch.setattr(file_extract, "_extract_from_image", lambda data: "1. 扫描题\n答案：A")

    text = file_extract._extract_from_pdf(b"fake-pdf")

    assert "扫描题" in text
    assert text.source == "ocr"


def _fake_ocr_setup(monkeypatch, responses):
    """装一个按 psm 返回预设文本的假 pytesseract，并记录被调用过哪些 psm。"""
    image = Image.new("RGB", (80, 80), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    calls = []

    def fake_ocr(_image, lang, config):
        psm = int(re.search(r"--psm (\d+)", config).group(1))
        calls.append(psm)
        return responses.get(psm, "")

    fake_module = SimpleNamespace(
        image_to_string=fake_ocr,
        pytesseract=SimpleNamespace(tesseract_cmd=""),
    )
    monkeypatch.setitem(sys.modules, "pytesseract", fake_module)
    monkeypatch.setattr(file_extract, "_configure_tesseract_binary", lambda _module: None)
    return output.getvalue(), calls


def test_image_ocr_stops_after_first_sufficient_pass(monkeypatch) -> None:
    """首趟就切出完整题且覆盖率达标时，不再跑剩下的 psm（每趟都是 2s+ 的子进程）。"""
    payload, calls = _fake_ocr_setup(
        monkeypatch,
        {
            6: "1. 第一题\n答案：甲",
            4: "1. 第一题\n答案：甲\n2. 第二题\n答案：乙",
            11: "无法形成题目",
        },
    )

    text = file_extract._extract_from_image(payload)

    assert calls == [6]
    assert "第一题" in text


def test_image_ocr_tries_next_psm_when_first_pass_is_insufficient(monkeypatch) -> None:
    """首趟没拆出题时才换版面假设，且一旦够好就停。"""
    payload, calls = _fake_ocr_setup(
        monkeypatch,
        {
            6: "无法形成题目",
            4: "1. 第一题\n答案：甲\n2. 第二题\n答案：乙",
            11: "无法形成题目",
        },
    )

    text = file_extract._extract_from_image(payload)

    assert calls == [6, 4]
    assert "第二题" in text


def test_image_ocr_runs_all_psm_passes_when_fast_accept_disabled(monkeypatch) -> None:
    """OCR_FAST_ACCEPT=0 时退回「三趟全跑、取最优」，用于追求最大召回的场景。"""
    monkeypatch.setattr(file_extract, "_OCR_FAST_ACCEPT", False)
    payload, calls = _fake_ocr_setup(
        monkeypatch,
        {
            4: "1. 第一题\n答案：甲\n2. 第二题\n答案：乙",
            6: "1. 只有一题\n答案：甲",
            11: "无法形成题目",
        },
    )

    text = file_extract._extract_from_image(payload)

    assert calls == [6, 4, 11]
    assert "第二题" in text
    assert "只有一题" not in text


def test_image_ocr_prefers_coverage_over_text_length(monkeypatch) -> None:
    """题数相同时按覆盖率选，而不是按字符数选。"""
    image = Image.new("RGB", (80, 80), "white")
    output = BytesIO()
    image.save(output, format="PNG")

    def fake_ocr(_image, lang, config):
        psm = int(re.search(r"--psm (\d+)", config).group(1))
        if psm == 6:
            # 1 道完整题 + 1 个残块（第二题缺答案）→ coverage 0.5，但文本更长
            return "1. 甲\n答案：A\n2. 乙"
        if psm == 4:
            # 1 道完整题，无残块 → coverage 1.0，文本更短
            return "1. 甲\n答案：A"
        return ""

    fake_module = SimpleNamespace(
        image_to_string=fake_ocr,
        pytesseract=SimpleNamespace(tesseract_cmd=""),
    )
    monkeypatch.setitem(sys.modules, "pytesseract", fake_module)
    monkeypatch.setattr(file_extract, "_configure_tesseract_binary", lambda _module: None)

    text = file_extract._extract_from_image(output.getvalue())

    assert text == "1. 甲\n答案:A"


def test_image_ocr_does_not_downscale_by_default(monkeypatch) -> None:
    """默认不缩放：实测缩小会抹掉选项句点（选项 3→0）、3000px 时还会丢题。

    这条测试是为了防止后人"优化"出缩小逻辑：省下的 0.2s 预处理不值这个准确率。
    """
    image = Image.new("RGB", (4000, 3000), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    seen = []

    def fake_ocr(img, lang, config):
        seen.append(img.size)
        return "1. 第一题\n答案：甲"

    fake_module = SimpleNamespace(
        image_to_string=fake_ocr,
        pytesseract=SimpleNamespace(tesseract_cmd=""),
    )
    monkeypatch.setitem(sys.modules, "pytesseract", fake_module)
    monkeypatch.setattr(file_extract, "_configure_tesseract_binary", lambda _module: None)

    file_extract._extract_from_image(output.getvalue())

    assert seen == [(4000, 3000)]


def test_clean_extracted_text_ocr_mode_fixes_common_ocr_errors() -> None:
    raw = "１． 第一题\r\n\r\n\r\nl. 第二题\r\n答桉：A\r\n解忻：略"

    cleaned = file_extract.clean_extracted_text(raw, ocr=True)

    assert cleaned == "1. 第一题\n1. 第二题\n答案:A\n解析:略"


def test_clean_extracted_text_keeps_non_ocr_behaviour_unchanged() -> None:
    raw = "第一章 基础\r\n\r\n\r\n答桉：A\n\n\n\n正文"

    cleaned = file_extract.clean_extracted_text(raw)

    # 非 OCR 路径不做错字纠正、不转全角标点，只压空行
    assert cleaned == "第一章 基础\n\n答桉：A\n\n正文"


def test_image_text_goes_through_unified_cleaning(monkeypatch) -> None:
    """图片分支不再绕过 clean_extracted_text（page 噪声/空行同样被清理）。"""
    monkeypatch.setattr(
        file_extract,
        "_extract_from_image",
        lambda data: "1. 甲\n答案：A\n\n\n\n12\n正文",
    )

    text = file_extract.extract_text_from_file("a.png", b"fake-image")

    assert "12" not in text
    assert "\n\n\n" not in text
    assert "正文" in text
    assert text.source == "ocr"
