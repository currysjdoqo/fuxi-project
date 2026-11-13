import json
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


def test_image_ocr_tries_three_psm_modes_and_selects_most_questions(monkeypatch) -> None:
    image = Image.new("RGB", (80, 80), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    calls = []

    def fake_ocr(_image, lang, config):
        psm = int(config.rsplit(" ", 1)[-1])
        calls.append(psm)
        if psm == 4:
            return "1. 第一题\n答案：甲\n2. 第二题\n答案：乙"
        if psm == 6:
            return "1. 只有一题\n答案：甲"
        return "无法形成题目"

    fake_module = SimpleNamespace(
        image_to_string=fake_ocr,
        pytesseract=SimpleNamespace(tesseract_cmd=""),
    )
    monkeypatch.setitem(sys.modules, "pytesseract", fake_module)
    monkeypatch.setattr(file_extract, "_configure_tesseract_binary", lambda _module: None)

    text = file_extract._extract_from_image(output.getvalue())

    assert calls == [6, 4, 11]
    assert "第二题" in text
    assert "只有一题" not in text
