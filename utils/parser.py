"""题目文本解析器。

设计目标：用「规则表 + 多策略匹配 + 行内拆分 + 残块回收」覆盖常见题库文本格式，
而不是绑定单一模板。整个项目只有这一处「文本 → 题目」的实现，导入预览、批量解析、
智能解析、残块 AI 补解析都复用它。

扩展方式：需要支持新的编号 / 选项 / 答案 / 解析写法时，只需在下方对应规则表中追加一条正则，
主解析流程无需改动。

解析结果分三部分返回（parse_exercise_text_detailed）：
- questions：完整可入库的题目
- residuals：识别到题目开头但缺关键信息（多为答案）的残块，供 AI 只补这些片段
- stats：block 数、覆盖率等，用于决定是否值得调用 AI
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .answer_normalizer import normalize_standard_answer
from .file_extract import TEXT_EXTRACT_EXTENSIONS, extract_text_from_file


# ============================ 全角折叠 ============================
# 只折叠「标记字符」，不折叠中文逗号句号，避免污染题面展示。
# 映射全部是 1 字符 → 1 字符，折叠后的下标与原文对齐，可用折叠串定位再切原文。
_FOLD_MAP: Dict[str, str] = {}
for _i in range(10):
    _FOLD_MAP[chr(0xFF10 + _i)] = chr(0x30 + _i)          # ０-９
for _i in range(26):
    _FOLD_MAP[chr(0xFF21 + _i)] = chr(0x41 + _i)          # Ａ-Ｚ
    _FOLD_MAP[chr(0xFF41 + _i)] = chr(0x61 + _i)          # ａ-ｚ
_FOLD_MAP.update(
    {
        "：": ":",
        "；": ";",
        "（": "(",
        "）": ")",
        "［": "[",
        "］": "]",
        "【": "[",
        "】": "]",
        "．": ".",
        "　": " ",
        "\u00a0": " ",
        "\u3000": " ",
        "\u200b": "",
        "\ufeff": "",
        "／": "/",
        "＋": "+",
        "－": "-",
        "—": "-",
        "–": "-",
        "～": "~",
    }
)
_FOLD_TABLE = str.maketrans(_FOLD_MAP)

CIRCLED_NUMBERS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def _fold(line: str) -> str:
    return line.translate(_FOLD_TABLE)


# ============================ 规则表 ============================
# --- 题型分组标题（如“一、单选题（共10题）”“【多选题】”）---
HEADER_RE = re.compile(
    r"^\s*(?:[一二三四五六七八九十]+\s*[.、]\s*)?[\[(]?\s*"
    r"(?:单选题|单项选择题|多选题|多项选择题|不定项选择题|选择题|"
    r"判断题|填空题|简答题|论述题|编程题|代码题)"
    r"\s*[\])]?.*"
)

# --- 题目编号（整行只有编号）---
QUESTION_NUM_ONLY_PATTERNS = [
    re.compile(r"^\s*#{1,6}\s*\d{1,3}\s*[.、)]?\s*$"),                       # ## 1
    re.compile(r"^\s*\d{1,3}\s*[.、)]\s*$"),                                 # 1. / 1、 / 1)
    re.compile(r"^\s*\(\s*\d{1,3}\s*\)\s*$"),                                # (1) / （1）
    re.compile(r"^\s*第\s*\d{1,3}\s*题\s*[.、:]?\s*$"),                       # 第1题
    re.compile(r"^\s*\[\s*\d{1,3}\s*\]\s*$"),                                 # 【1】
    re.compile(r"^\s*[Qq]\s*\d{1,3}\s*[.、):]\s*$"),                         # Q1.
    re.compile(r"^\s*(?:例题?|题目)\s*\d{1,3}\s*[.、:]?\s*$"),                 # 例1 / 例题1
    re.compile(r"^\s*(?:question|item)\s*\d{1,3}\s*[.):]?\s*$", re.IGNORECASE),
    re.compile(r"^\s*[%s]\s*$" % CIRCLED_NUMBERS),                            # ①
]

# --- 题目编号 + 内容同行（编号后不能紧跟数字，避免把 IP / 小数误判为编号）---
QUESTION_NUM_CONTENT_PATTERNS = [
    re.compile(r"^\s*#{1,6}\s*\d{1,3}\s*[.、)]?\s+(?!\d)(.+)$"),              # ## 1 题干
    re.compile(r"^\s*\d{1,3}\s*[.、)]\s*(?!\d)(.+)$"),                        # 1. 题干
    re.compile(r"^\s*\(\s*\d{1,3}\s*\)\s*(?!\d)(.+)$"),                       # (1) 题干
    re.compile(r"^\s*第\s*\d{1,3}\s*题\s*[.、:]?\s*(?!\d)(.+)$"),              # 第1题 题干
    re.compile(r"^\s*\[\s*\d{1,3}\s*\]\s*(?!\d)(.+)$"),                        # 【1】题干
    re.compile(r"^\s*[Qq]\s*\d{1,3}\s*[.、):]\s*(?!\d)(.+)$"),                 # Q1. 题干
    re.compile(r"^\s*(?:例题?|题目)\s*\d{1,3}\s*[.、:]?\s*(?!\d)(.+)$"),        # 例1 题干
    re.compile(r"^\s*(?:question|item)\s*\d{1,3}\s*[.):]?\s*(?!\d)(.+)$", re.IGNORECASE),
    re.compile(r"^\s*([%s])\s*(?!\d)(.+)$" % CIRCLED_NUMBERS),                 # ①题干
]

# --- 选项（单行一个选项）---
OPTION_PATTERNS = [
    re.compile(r"^\s*[\(\[]\s*([A-Ha-h])\s*[\)\]]\s*[.、:]?\s*(.*)$"),         # (A) / [A]
    re.compile(r"^\s*([A-Ha-h])\s*[.、):]\s*(.*)$"),                           # A、 / A. / A) / A:
]

# --- 一行多个选项（如 “A、甲 B、乙 C、丙 D、丁”）---
INLINE_OPTION_MARK_RE = re.compile(r"(?<![A-Za-z0-9])([A-H])\s*[.、):]\s*")

# --- 解析标签（解析优先于答案判断，避免 “答案解析” 被误当答案）---
EXPLANATION_PATTERNS = [
    re.compile(r"^\s*\*{0,2}\s*(?:答案解析|试题解析|题目解析|答案详解|解析|详解|分析)\s*\*{0,2}\s*:\s*(.*)$"),
    re.compile(r"^\s*\[\s*(?:解析|详解|答案解析|分析)\s*\]\s*:?\s*(.*)$"),
]

# --- 答案标签 ---
ANSWER_PATTERNS = [
    re.compile(r"[\[\(]\s*(?:正确答案|参考答案|标准答案|答案)\s*[\])]\s*:?\s*(.*)$"),
    re.compile(r"\*{0,2}\s*(?:正确答案|参考答案|标准答案)\s*\*{0,2}\s*:\s*\*{0,2}\s*(.*?)\s*\*{0,2}\s*$"),
    re.compile(r"\*{0,2}\s*答案\s*\*{0,2}\s*:\s*(?!解析)\s*\*{0,2}\s*(.*?)\s*\*{0,2}\s*$"),
]

# --- 行内答案（题干与答案挤在同一行，最常见于 PDF/网页复制）---
# --- 行内答案（题干与答案挤在同一行，可出现在行中任意位置）---
_INLINE_ANSWER_ANY_RE = re.compile(
    r"[(（【]?\s*(?:正确答案|参考答案|标准答案|答案)\s*[:]\s*"
    r"([A-Ha-h]{1,4}|对|错|正确|错误|√|×|✓|✕|[TtFf]|\d{1,6})\s*[)）】]?"
)

INLINE_ANSWER_RE = re.compile(
    r"\s*[\[\(]?\s*(?:正确答案|参考答案|标准答案|答案)\s*[\])]?\s*(?::\s*|\s+)"
    r"([A-Ha-h]{1,8}|对|错|正确|错误|√|×|✓|✕|T|F)\s*[。.;]?\s*$"
)

# --- 行内解析（题干后紧跟“解析：……”）---
INLINE_EXPLANATION_RE = re.compile(
    r"\s*[\[\(]?\s*(?:答案解析|试题解析|题目解析|答案详解|解析|详解|分析)\s*[\])]?\s*:\s*(.*)$"
)

# --- 同一行里塞了多道题（PDF 提取常见：“1.xxx 2.yyy 3.zzz”）---
MERGED_NUMBER_RE = re.compile(r"(?:(?<=\s)|(?<=[。.;!?！？；：]))(\d{1,3})\s*[.、)]\s*(?=\S)")

# --- 章节标题：第一章 绪论 / 第1章 绪论 / Chapter 2 xxx / 1.1 xxx / 一、绪论 ---
CHAPTER_TITLE_RES = [
    re.compile(r"^\s*第\s*[0-9零一二三四五六七八九十百]+\s*[章节篇部](?:\s*[:、.\-]\s*|\s+).+$"),
    re.compile(r"^\s*第\s*[0-9零一二三四五六七八九十百]+\s*[章节篇部]\s*$"),
    re.compile(r"^\s*chapter\s+\d+(?:\s*[:.\-]\s*|\s+).+$", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\d+(?:\.\d+)?(?:\s*[:、.\-]\s*|\s+).+$"),
    re.compile(r"^\s*[一二三四五六七八九十]+\s*[、.]\s*.+$"),
]

CHAPTER_TITLE_MAX_LEN = 40

# --- 噪声行：页码、页眉页脚残留、“第 X 页 共 Y 页” ---
NOISE_LINE_RES = [
    re.compile(r"^\s*[-—–]?\s*\d{1,4}\s*[-—–]?\s*$"),
    re.compile(r"^\s*第\s*\d{1,4}\s*页(\s*[，,/]?\s*共\s*\d{1,4}\s*页)?\s*$"),
    re.compile(r"^\s*共\s*\d{1,4}\s*页\s*$"),
    re.compile(r"^\s*page\s*\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*$", re.IGNORECASE),
    re.compile(r"^\s*[-—–=*_·.。\s]{1,20}$"),
]

TYPE_LABELS = {
    "single": "单选题",
    "multi": "多选题",
    "judge": "判断题",
    "fill": "填空题",
    "short": "简答题",
    "code": "编程题",
}

# 分块统计时用：一行是否「像」一道题的开头
QUESTION_START_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\d{1,3}\s*[.、)]|\(\s*\d{1,3}\s*\)|第\s*\d{1,3}\s*题|"
    r"\[\s*\d{1,3}\s*\]|[Qq]\s*\d{1,3}\s*[.、):]|(?:例题?|题目)\s*\d{1,3}|"
    r"(?:question|item)\s*\d{1,3}|[%s])" % CIRCLED_NUMBERS,
    re.IGNORECASE,
)


# ============================ 匹配辅助 ============================

def _match_chapter_title(line: str) -> str | None:
    """识别章节标题行，返回章节名；不是标题返回 None。"""
    if len(line) > CHAPTER_TITLE_MAX_LEN or "?" in line or "？" in line:
        return None
    # 题型分组标题（如“一、单选题（共10题）”）不是章节
    if _type_from_header(line) and HEADER_RE.match(line):
        return None
    for pattern in CHAPTER_TITLE_RES:
        if pattern.match(line):
            return line.strip()
    return None


def _clean_lines(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in normalized.split("\n")]


def _is_noise_line(line: str) -> bool:
    return any(pattern.match(line) for pattern in NOISE_LINE_RES)


def _type_from_header(line: str) -> str | None:
    if any(k in line for k in ("多选题", "多项选择题", "不定项选择题")):
        return "multi"
    if "判断题" in line:
        return "judge"
    if "填空题" in line:
        return "fill"
    if any(k in line for k in ("简答题", "论述题")):
        return "short"
    if any(k in line for k in ("编程题", "代码题")):
        return "code"
    if "单选题" in line or "选择题" in line:
        return "single"
    return None


def _is_question_number_only(line: str) -> bool:
    return any(p.match(line) for p in QUESTION_NUM_ONLY_PATTERNS)


def _match_question_number_with_content(line: str) -> str | None:
    for p in QUESTION_NUM_CONTENT_PATTERNS:
        m = p.match(line)
        if m:
            return m.groups()[-1].strip()
    return None


def _match_option(line: str) -> tuple[str, str] | None:
    for p in OPTION_PATTERNS:
        m = p.match(line)
        if m:
            return m.group(1).upper(), m.group(2).strip()
    return None


def _split_inline_options(line: str) -> list[tuple[str, str]] | None:
    """把 “A、甲 B、乙 C、丙” 这类一行多选项拆开；不像选项则返回 None。"""
    marks = list(INLINE_OPTION_MARK_RE.finditer(line))
    if len(marks) < 2 or marks[0].start() != 0:
        return None
    letters = [m.group(1) for m in marks]
    if letters != list("ABCDEFGH"[: len(letters)]):
        return None
    options = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(line)
        options.append((m.group(1), line[m.end():end].strip()))
    # 任一项为空则不认为是选项行，避免误伤
    if any(not value for _, value in options):
        return None
    return options


def _extract_options_anywhere(text: str) -> tuple[str, list[tuple[str, str]]] | None:
    """在“题干 + 选项挤在一行”的文本尾部找 A/B/C/D 选项，返回 (题干, 选项)。

    只接受从 A 开始连续、每项非空、且题干非空的情况，避免误伤正文。
    """
    marks = list(INLINE_OPTION_MARK_RE.finditer(text))
    if len(marks) < 2:
        return None
    # 从第一个 A 开始
    start_index = None
    for i, m in enumerate(marks):
        if m.group(1) == "A":
            start_index = i
            break
    if start_index is None:
        return None
    tail = marks[start_index:]
    letters = [m.group(1) for m in tail]
    if letters != list("ABCDEFGH"[: len(letters)]):
        return None
    options = []
    for i, m in enumerate(tail):
        end = tail[i + 1].start() if i + 1 < len(tail) else len(text)
        options.append((m.group(1), text[m.end():end].strip()))
    if any(not value for _, value in options):
        return None
    content = text[: tail[0].start()].strip()
    if not content:
        return None
    return content, options


def _match_explanation(line: str) -> str | None:
    """返回解析正文；不是解析行返回 None。"""
    for p in EXPLANATION_PATTERNS:
        m = p.match(line)
        if m:
            return m.group(1).strip()
    return None


def _match_answer(line: str) -> str | None:
    """返回答案原文；不是答案行返回 None。"""
    for p in ANSWER_PATTERNS:
        m = p.search(line)
        if m:
            return m.group(1).strip()
    return None


def _split_inline_answer(line: str) -> tuple[str, str] | None:
    """行内答案：返回 (答案前的正文, 答案)；没有则 None。"""
    m = INLINE_ANSWER_RE.search(line)
    if not m:
        return None
    body = line[: m.start()].rstrip()
    if not body:
        return None
    return body, m.group(1)


def _split_inline_explanation(line: str) -> tuple[str, str] | None:
    m = INLINE_EXPLANATION_RE.search(line)
    if not m:
        return None
    return line[: m.start()].rstrip(), m.group(1).strip()


def _strip_inline_answers(line: str) -> tuple[str, str]:
    """删除行内所有“答案：X”片段，返回 (剩余文本, 首个答案)。"""
    first_answer = ""
    pieces: list[str] = []
    last_end = 0
    for m in _INLINE_ANSWER_ANY_RE.finditer(line):
        pieces.append(line[last_end:m.start()])
        last_end = m.end()
        if not first_answer:
            first_answer = m.group(1)
    if not first_answer:
        return line, ""
    pieces.append(line[last_end:])
    remainder = "".join(pieces)
    remainder = re.sub(r"[ \t]{2,}", " ", remainder).strip(" 　,，;；")
    return remainder, first_answer


def _split_merged_questions(line: str) -> list[str]:
    matches = list(MERGED_NUMBER_RE.finditer(line))
    if not matches:
        return [line]
    numbers = [int(m.group(1)) for m in matches]
    if len(numbers) < 2 or any(current <= previous for previous, current in zip(numbers, numbers[1:])):
        return [line]
    if numbers[0] == 1 and line[:matches[0].start()].strip():
        return [line]
    segments: list[str] = []
    if matches[0].start() > 0:
        segments.append(line[: matches[0].start()].strip())
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        segments.append(line[m.start():end].strip())
    return [segment for segment in segments if segment]


def _new_question(section_type: str, chapter_name: str | None) -> dict:
    return {
        "type": section_type,
        "content": [],
        "options": {},
        "answer": "",
        "_answer_lines": [],
        "explanation": [],
        "chapter_name": chapter_name,
    }


# ============================ 归一化与收尾 ============================

def _infer_type_from_content(question: dict) -> str:
    content = "\n".join(question.get("content", []))
    if question.get("options"):
        if question.get("type") == "multi":
            return "multi"
        if question.get("type") == "judge":
            return "judge"
        return "single"
    answer = (question.get("answer") or "").strip()
    if question.get("type") == "single":
        # 没有选项且答案不是选项字母 → 更像填空题
        if not re.fullmatch(r"[A-Fa-f]{1,4}", answer or ""):
            return "fill"
        code_keywords = ["编程", "程序", "代码", "函数", "算法", "实现", "请写", "输入", "输出"]
        if any(keyword in content for keyword in code_keywords):
            return "code"
    return question.get("type", "single")


def _is_complete(question: dict | None) -> bool:
    if not question:
        return False
    if not question.get("content"):
        return False
    if question.get("type") == "judge" and question.get("answer") not in question.get("options", {}):
        return False
    if question.get("answer"):
        return True
    return question.get("type") in {"short", "code"}


def _drop_reason(question: dict | None) -> str:
    if not question:
        return "空块"
    if not question.get("content"):
        return "缺少题干"
    if not question.get("answer") and question.get("type") not in {"short", "code"}:
        return "缺少答案"
    return "信息不完整"


def _finalize_question(question: dict) -> dict:
    content = question.get("content", [])
    explanation = question.get("explanation", [])
    question["content"] = [content] if isinstance(content, str) else list(content or [])
    question["explanation"] = [explanation] if isinstance(explanation, str) else list(explanation or [])
    question["options"] = question.get("options") or {}
    question["type"] = _infer_type_from_content(question)
    raw_answer = str(question.get("answer") or "").strip()
    if not raw_answer and question.get("_answer_lines"):
        raw_answer = "\n".join(question["_answer_lines"]).strip()
    if question["type"] == "single" and re.fullmatch(r"[A-Z]+", raw_answer.upper()) and len(set(raw_answer.upper())) > 1:
        question["type"] = "multi"
    question["answer"] = normalize_standard_answer(question["type"], raw_answer)
    question["content"] = "\n".join(question["content"]).strip()
    question["explanation"] = "\n".join(question["explanation"]).strip()
    question["options"] = {
        str(key).upper(): str(value).strip()
        for key, value in question["options"].items()
        if str(value).strip()
    }
    question.pop("_answer_lines", None)
    if question["type"] == "judge":
        question["options"] = {"T": "正确", "F": "错误"}
    return question


def _finish_question(question: dict | None, raw_lines: list[str]) -> dict | None:
    """收尾当前题；返回完成后的题目（不完整时也返回，由调用方判断是否丢弃）。"""
    if not question:
        return None
    _finalize_question(question)
    question["_raw"] = "\n".join(raw_lines).strip()
    return question


# ============================ 主解析流程 ============================

def _apply_content_line(question: dict, text: str) -> None:
    """把一行正文并入当前题：先拆解析、再拆答案、再拆行内选项。"""
    text = text.strip()
    if not text:
        return

    inline_explanation = _split_inline_explanation(text)
    if inline_explanation:
        body, explanation = inline_explanation
        if body:
            _apply_content_line(question, body)
        if explanation:
            exp_remainder, exp_answer = _strip_inline_answers(explanation)
            if exp_answer and not question["answer"]:
                question["answer"] = exp_answer
            if exp_remainder:
                question["explanation"].append(exp_remainder)
        return

    remainder, inline_answer = _strip_inline_answers(text)
    if inline_answer:
        if not question["answer"]:
            question["answer"] = inline_answer
        if remainder:
            _apply_content_line(question, remainder)
        return

    if not question["options"]:
        split = _extract_options_anywhere(text)
        if split:
            content, options = split
            question["content"].append(content)
            for key, value in options:
                question["options"][key] = value
            return

    question["content"].append(text)


def _parse_lines(text: str, default_type: str = "single") -> Dict[str, Any]:
    questions: list[dict] = []
    residuals: list[dict] = []
    current: dict | None = None
    current_raw: list[str] = []
    current_section_type = default_type
    current_chapter_name: str | None = None
    mode = "idle"
    last_option: str | None = None
    marker_count = 0
    unattributed_raw: list[str] = []
    unattributed_lines = 0

    def flush(reason: str = "") -> None:
        nonlocal current, current_raw
        if current is None:
            return
        finished = _finish_question(current, current_raw)
        position = len(questions) + len(residuals)
        if finished and _is_complete(finished):
            finished.pop("_raw", None)
            finished["_order"] = position
            questions.append(finished)
        elif finished:
            finished.pop("_raw", None)
            residuals.append(
                {
                    "reason": reason or _drop_reason(finished),
                    "text": "\n".join(current_raw).strip(),
                    "chapter_name": finished.get("chapter_name") or "",
                    "index": position + 1,
                    "order": position,
                }
            )
        current = None
        current_raw = []

    def flush_unattributed() -> None:
        nonlocal unattributed_raw
        if not unattributed_raw:
            return
        position = len(questions) + len(residuals)
        residuals.append(
            {
                "reason": "未归属正文",
                "text": "\n".join(unattributed_raw).strip(),
                "chapter_name": current_chapter_name or "",
                "index": position + 1,
                "order": position,
            }
        )
        unattributed_raw = []

    def start(line: str, first_content: str | None = None) -> None:
        nonlocal current, current_raw, mode, last_option
        flush_unattributed()
        flush()
        current = _new_question(current_section_type, current_chapter_name)
        current_raw = [line]
        mode = "content"
        last_option = None
        if first_content:
            _apply_content_line(current, first_content)

    for raw_line in _clean_lines(text):
        line = _fold(raw_line).strip()
        if not line:
            continue
        if _is_noise_line(line):
            continue

        # 1) 题型分组标题
        header_type = _type_from_header(line)
        if header_type and HEADER_RE.match(line):
            flush()
            flush_unattributed()
            current_section_type = header_type
            mode = "idle"
            continue

        # 2) 章节标题：切换当前章节，后续题目自动归属
        chapter_title = _match_chapter_title(line)
        if chapter_title:
            flush()
            flush_unattributed()
            current_chapter_name = raw_line.strip()
            mode = "idle"
            last_option = None
            continue

        # 3) 一行多题：先按编号切段，再分别当新题处理
        merged_segments = _split_merged_questions(line)
        if len(merged_segments) > 1:
            first_segment = merged_segments[0]
            first_folded = _fold(first_segment)
            first_is_question = (
                _match_question_number_with_content(first_folded) is not None
                or _is_question_number_only(first_folded)
            )
            if not first_is_question:
                if current is not None:
                    current_raw.append(raw_line)
                    _apply_content_line(current, first_segment)
                merged_segments = merged_segments[1:]

            question_segments = [
                segment
                for segment in merged_segments
                if _match_question_number_with_content(_fold(segment)) is not None
                or _is_question_number_only(_fold(segment))
            ]
            if question_segments:
                marker_count += len(question_segments)
                for segment in question_segments:
                    start(segment, _match_question_number_with_content(_fold(segment)))
                continue

        # 4) 新题目：编号单独一行，或编号与题干同行
        if _is_question_number_only(line):
            marker_count += 1
            start(raw_line)
            continue
        inline_content = _match_question_number_with_content(line)
        if inline_content is not None:
            marker_count += 1
            start(raw_line, inline_content)
            continue

        if current is None:
            unattributed_raw.append(raw_line.strip())
            unattributed_lines += 1
            continue

        # 4) 解析标签（先于答案判断，避免 “答案解析” 被当答案）
        explanation_text = _match_explanation(line)
        if explanation_text is not None:
            mode = "explanation"
            last_option = None
            if explanation_text:
                current["explanation"].append(explanation_text)
            current_raw.append(raw_line)
            continue

        # 5) 答案标签
        answer_text = _match_answer(line)
        if answer_text is not None and not current["answer"]:
            if answer_text:
                current["answer"] = answer_text
            mode = "answer"
            last_option = None
            current_raw.append(raw_line)
            continue

        # 6) 选项（含一行多选项）；答案先出现时也允许后面跟选项
        if current["type"] in {"single", "multi", "judge"} and mode != "explanation":
            inline_options = _split_inline_options(line)
            if inline_options:
                for key, value in inline_options:
                    current["options"][key] = value
                mode = "options"
                last_option = inline_options[-1][0]
                current_raw.append(raw_line)
                continue
            option = _match_option(line)
            if option:
                key, value = option
                current["options"][key] = value
                mode = "options"
                last_option = key
                current_raw.append(raw_line)
                continue

        # 7) 续行归属
        current_raw.append(raw_line)
        if mode == "content":
            _apply_content_line(current, line)
        elif mode == "options" and last_option:
            current["options"][last_option] = f"{current['options'][last_option]}\n{line}".strip()
        elif mode == "answer" and not current["answer"]:
            current["_answer_lines"].append(line)
        elif mode in {"answer", "explanation"}:
            current["explanation"].append(line)

    flush()
    flush_unattributed()

    estimated_residual_questions = sum(
        max(1, sum(bool(QUESTION_START_RE.match(_fold(line))) for line in item["text"].splitlines()))
        for item in residuals
    )
    block_count = max(marker_count, len(questions) + estimated_residual_questions)
    parsed_count = len(questions)
    coverage = round(parsed_count / block_count, 4) if block_count else 0.0
    return {
        "questions": questions,
        "residuals": residuals,
        "stats": {
            "question_markers": marker_count,
            "parsed_count": parsed_count,
            "residual_count": len(residuals),
            "coverage": coverage,
            "unattributed_lines": unattributed_lines,
        },
    }


def parse_exercise_text_detailed(text: str, *, default_type: str = "single") -> Dict[str, Any]:
    """解析文本，返回 questions / residuals / stats（供智能解析与 AI 残块补解析使用）。"""
    result = _parse_lines(text or "", default_type)
    result["errors"] = [
        f"第 {item['index']} 题{item['reason']}：{(item['text'].splitlines() or [''])[0][:40]}"
        for item in result["residuals"]
    ]
    return result


def parse_exercise_text(text: str, *, default_type: str = "single") -> List[dict]:
    """解析题库文本（只要完整题目）。

    支持：
    - 编号：``1`` / ``1.`` / ``1、`` / ``1)`` / ``（1）`` / ``第1题`` / ``Q1.`` / ``## 1`` / ``①`` / ``例1``
    - 选项：``A、`` / ``A.`` / ``A)`` / ``A：`` / ``（A）`` / ``【A】``，以及一行多选项，
      以及“题干 + 选项挤在同一行”
    - 答案：``正确答案：`` / ``参考答案：`` / ``答案：`` / ``【答案】``（自动去掉 markdown 加粗），
      以及“题干…… 答案：A”这种行内答案
    - 解析：``解析：`` / ``答案解析：`` / ``【解析】`` / ``详解：``，以及行内解析
    - 题型分组标题、章节标题自动归属；页码/页眉等噪声行自动跳过
    """
    questions = _parse_lines(text, default_type)["questions"]
    for question in questions:
        question.pop("_order", None)
    return questions


def parse_structured_questions(raw_questions: list[Any], errors: list[str] | None = None) -> Dict[str, Any]:
    questions: list[dict] = []
    residuals: list[dict] = []
    result_errors = list(errors or [])

    for position, raw in enumerate(raw_questions):
        item = raw if isinstance(raw, dict) else {"content": str(raw), "_error": "题目格式错误"}
        question = _new_question(str(item.get("type") or "single"), item.get("chapter_name") or None)
        question["content"] = item.get("content") or []
        raw_options = item.get("options")
        if isinstance(raw_options, dict):
            question["options"] = raw_options
        elif isinstance(raw_options, str):
            for option_line in raw_options.splitlines() or [raw_options]:
                inline_options = _split_inline_options(_fold(option_line.strip()))
                if inline_options:
                    for key, value in inline_options:
                        question["options"][key] = value
                    continue
                option = _match_option(_fold(option_line.strip()))
                if option:
                    question["options"][option[0]] = option[1]
        question["answer"] = str(item.get("answer") or "").strip()
        question["explanation"] = item.get("explanation") or []
        question["_order"] = position
        _finalize_question(question)
        if not item.get("_error") and _is_complete(question):
            questions.append(question)
            continue

        content = question.get("content", "")
        raw_lines = [content] if content else []
        raw_lines.extend(f"{key}. {value}" for key, value in question.get("options", {}).items())
        if question.get("answer"):
            raw_lines.append(f"答案：{question['answer']}")
        residuals.append(
            {
                "reason": str(item.get("_error") or _drop_reason(question)),
                "text": str(item.get("_raw") or "\n".join(raw_lines)),
                "chapter_name": question.get("chapter_name") or "",
                "index": position + 1,
                "order": position,
            }
        )

    result_errors.extend(
        f"第 {item['index']} 题{item['reason']}：{(item['text'].splitlines() or [''])[0][:40]}"
        for item in residuals
    )
    total = len(raw_questions)
    return {
        "questions": questions,
        "residuals": residuals,
        "stats": {
            "question_markers": total,
            "parsed_count": len(questions),
            "residual_count": len(residuals),
            "coverage": round(len(questions) / total, 4) if total else 0.0,
            "unattributed_lines": 0,
            "source": "structured",
        },
        "errors": result_errors,
    }


def parse_file_detailed(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """按扩展名解析文件，返回与 parse_exercise_text_detailed 同构的结果。"""
    ext = Path(filename).suffix.lower()

    if ext in {".xlsx", ".xls", ".csv", ".json"}:
        from .import_template import parse_csv_to_questions, parse_excel_to_questions, parse_json_to_questions

        if ext in {".xlsx", ".xls"}:
            questions, errors = parse_excel_to_questions(file_bytes)
        elif ext == ".csv":
            questions, errors = parse_csv_to_questions(file_bytes)
        else:
            questions, errors = parse_json_to_questions(file_bytes)
        return parse_structured_questions(questions, errors)

    if ext == ".docx":
        from .file_extract import clean_extracted_text, extract_docx_content

        text, raw_questions = extract_docx_content(file_bytes)
        structured = parse_structured_questions(raw_questions)
        text_result = parse_exercise_text_detailed(clean_extracted_text(text), default_type="single")
        if not raw_questions:
            text_result["stats"]["source"] = "text"
            return text_result
        if not text:
            structured["stats"]["source"] = "docx_table"
            return structured

        offset = len(structured["questions"]) + len(structured["residuals"])
        for question in text_result["questions"]:
            question["_order"] = int(question.get("_order", 0)) + offset
        for residual in text_result["residuals"]:
            residual["order"] = int(residual.get("order", 0)) + offset
        questions = structured["questions"] + text_result["questions"]
        residuals = structured["residuals"] + text_result["residuals"]
        markers = structured["stats"]["question_markers"] + text_result["stats"]["question_markers"]
        total = max(markers, len(questions) + len(residuals))
        return {
            "questions": questions,
            "residuals": residuals,
            "stats": {
                "question_markers": markers,
                "parsed_count": len(questions),
                "residual_count": len(residuals),
                "coverage": round(len(questions) / total, 4) if total else 0.0,
                "unattributed_lines": text_result["stats"].get("unattributed_lines", 0),
                "source": "docx_table",
            },
            "errors": structured["errors"] + text_result["errors"],
        }

    if ext in TEXT_EXTRACT_EXTENSIONS:
        text = extract_text_from_file(filename, file_bytes)
        result = parse_exercise_text_detailed(text, default_type="single")
        result["stats"]["source"] = getattr(text, "source", "ocr" if ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"} else "text")
        return result

    return {
        "questions": [],
        "residuals": [],
        "stats": {"question_markers": 0, "parsed_count": 0, "residual_count": 0, "coverage": 0.0},
        "errors": [f"不支持的文件格式: {ext}"],
    }


def parse_file(file_bytes: bytes, filename: str) -> Tuple[List[dict], List[str]]:
    """
    根据文件扩展名自动选择解析方式
    :param file_bytes: 文件字节内容
    :param filename: 文件名（用于识别格式）
    :return: (解析出的题目列表, 错误信息列表)
    """
    result = parse_file_detailed(file_bytes, filename)
    return result["questions"], result["errors"]
