import re
from pathlib import Path
from typing import List, Tuple

from .file_extract import TEXT_EXTRACT_EXTENSIONS, extract_text_from_file


QUESTION_NO_RE = re.compile(r"^\s*\d+[.．、]?\s*$")
OPTION_RE = re.compile(r"^\s*([A-Z])[.、)]\s*(.*)$", re.IGNORECASE)
# 新增：匹配 "1. 题目内容" 这种格式的编号行
QUESTION_NO_WITH_CONTENT_RE = re.compile(r"^\s*\d+[.．、]\s*(.+)$")
ANSWER_RE = re.compile(r"(正确答案|参考答案|答案)\s*[:：]\s*(.*)")
EXPLANATION_RE = re.compile(r"^答案解析\s*[:：]\s*(.*)$")
HEADER_RE = re.compile(r"^\s*(?:[一二三四五六七八九十]+[.．、]\s*)?(单选题|多选题|多项选择题|选择题|判断题|填空题|简答题|编程题).*")

TYPE_LABELS = {
    "single": "单选题",
    "multi": "多选题",
    "judge": "判断题",
    "fill": "填空题",
    "short": "简答题",
    "code": "编程题",
}


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def _type_from_header(line: str) -> str | None:
    if "多选题" in line or "多项选择题" in line:
        return "multi"
    if "判断题" in line:
        return "judge"
    if "填空题" in line:
        return "fill"
    if "简答题" in line:
        return "short"
    if "编程题" in line:
        return "code"
    if "单选题" in line or "选择题" in line:
        return "single"
    return None


def _infer_type_from_content(question: dict) -> str:
    content = "\n".join(question.get("content", []))
    if question.get("options"):
        if question.get("type") == "multi":
            return "multi"
        if question.get("type") == "judge":
            return "judge"
        return "single"
    if question.get("type") == "single":
        code_keywords = ["编程", "程序", "代码", "函数", "算法", "实现", "请写", "输入", "输出"]
        if any(keyword in content for keyword in code_keywords):
            return "code"
    return question.get("type", "single")


def _normalize_answer(answer: str, question_type: str) -> str:
    answer = re.split(r"\s*我的答案\s*[:：]|\s*得分\s*[:：]", answer.strip())[0].strip()
    if question_type == "single":
        multi_like = re.findall(r"[A-Z]", answer.upper())
        if len(set(multi_like)) > 1:
            return "".join(sorted(set(multi_like)))
        match = re.search(r"[A-Z]", answer, re.IGNORECASE)
        return match.group(0).upper() if match else answer
    if question_type == "multi":
        letters = re.findall(r"[A-Z]", answer.upper())
        if not letters:
            return answer
        return "".join(sorted(set(letters)))
    if question_type == "judge":
        compact = "".join(answer.upper().split())
        if compact in {"对", "正确", "TRUE", "T", "YES", "Y", "A", "√", "✓", "✔"}:
            return "T"
        if compact in {"错", "错误", "FALSE", "F", "NO", "N", "B", "×", "✕", "✖", "X"}:
            return "F"
    return answer


def _is_complete(question: dict | None) -> bool:
    if not question:
        return False
    if not question.get("content"):
        return False
    if question.get("answer"):
        return True
    return question.get("type") in {"short", "code"}


def _finish_question(question: dict | None, questions: list[dict]) -> None:
    if not question:
        return

    # Infer type first so short/code questions can be kept even without a standard answer.
    question["type"] = _infer_type_from_content(question)

    if question and not question.get("answer") and question.get("_answer_lines"):
        question["answer"] = _normalize_answer("\n".join(question["_answer_lines"]), question["type"])
    if not _is_complete(question):
        return

    if question["type"] == "single" and re.fullmatch(r"[A-Z]+", question["answer"].upper()) and len(set(question["answer"].upper())) > 1:
        question["type"] = "multi"
    question["content"] = "\n".join(question["content"]).strip()
    question["explanation"] = "\n".join(question["explanation"]).strip()
    question["options"] = {key: value.strip() for key, value in question["options"].items() if value.strip()}
    question.pop("_answer_lines", None)
    if question["type"] == "judge" and not question["options"]:
        question["options"] = {"T": "正确", "F": "错误"}
    questions.append(question)


def parse_exercise_text(text: str) -> List[dict]:
    """
    Parse single-choice, multi-choice, judge, fill-in-blank and short-answer exercises.

    Supported answer labels:
    - 正确答案：...
    - 参考答案：...
    - 答案：...

    Sections like "一.单选题（共10题,100.0分）" set the current type.
    A line containing only digits starts a new question.
    """
    questions: list[dict] = []
    current: dict | None = None
    current_section_type = "single"
    mode = "idle"
    last_option: str | None = None

    for raw_line in _clean_lines(text):
        line = raw_line.strip()
        if not line or line.lower() == "text":
            continue

        header_type = _type_from_header(line)
        if header_type and HEADER_RE.match(line):
            current_section_type = header_type
            continue

        if QUESTION_NO_RE.match(line):
            _finish_question(current, questions)
            current = {
                "type": current_section_type,
                "content": [],
                "options": {},
                "answer": "",
                "_answer_lines": [],
                "explanation": [],
            }
            mode = "content"
            last_option = None
            continue

        # 支持 "1. 题目内容" 格式，编号和题目在同一行
        question_with_content_match = QUESTION_NO_WITH_CONTENT_RE.match(line)
        if question_with_content_match:
            _finish_question(current, questions)
            current = {
                "type": current_section_type,
                "content": [question_with_content_match.group(1)],
                "options": {},
                "answer": "",
                "_answer_lines": [],
                "explanation": [],
            }
            mode = "content"
            last_option = None
            continue

        if current is None:
            continue

        option_match = OPTION_RE.match(line)
        if option_match and not current["answer"] and current["type"] in {"single", "multi", "judge"}:
            key = option_match.group(1).upper()
            if current["type"] not in {"single", "multi", "judge"}:
                current["type"] = "single"
            current["options"][key] = option_match.group(2).strip()
            mode = "options"
            last_option = key
            continue

        answer_match = ANSWER_RE.search(line)
        if answer_match and not line.startswith("答案解析"):
            answer_text = answer_match.group(2).strip()
            if answer_text:
                current["answer"] = _normalize_answer(answer_text, current["type"])
            mode = "answer"
            last_option = None
            continue

        explanation_match = EXPLANATION_RE.match(line)
        if explanation_match:
            mode = "explanation"
            last_option = None
            inline_explanation = explanation_match.group(1).strip()
            if inline_explanation:
                current["explanation"].append(inline_explanation)
            continue

        if mode == "content":
            current["content"].append(line)
        elif mode == "options" and last_option:
            current["options"][last_option] = f"{current['options'][last_option]}\n{line}".strip()
        elif mode == "answer" and not current["answer"]:
            current["_answer_lines"].append(line)
        elif mode in {"answer", "explanation"}:
            current["explanation"].append(line)

    _finish_question(current, questions)
    return questions


def parse_file(file_bytes: bytes, filename: str) -> Tuple[List[dict], List[str]]:
    """
    根据文件扩展名自动选择解析方式
    :param file_bytes: 文件字节内容
    :param filename: 文件名（用于识别格式）
    :return: (解析出的题目列表, 错误信息列表)
    """
    ext = Path(filename).suffix.lower()
    
    if ext in ['.xlsx', '.xls']:
        from .import_template import parse_excel_to_questions
        return parse_excel_to_questions(file_bytes)
    
    elif ext == '.csv':
        from .import_template import parse_csv_to_questions
        return parse_csv_to_questions(file_bytes)
    
    elif ext == '.json':
        from .import_template import parse_json_to_questions
        return parse_json_to_questions(file_bytes)
    
    elif ext in TEXT_EXTRACT_EXTENSIONS:
        text = extract_text_from_file(filename, file_bytes)
        questions = parse_exercise_text(text)
        return questions, []
    
    else:
        return [], [f"不支持的文件格式: {ext}"]
