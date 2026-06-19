import re


VALID_QUESTION_TYPES = {"single", "multi", "judge", "fill", "short", "code"}
JUDGE_TRUE_ALIASES = {"对", "正确", "TRUE", "T", "YES", "Y", "A", "√", "✅", "✔"}
JUDGE_FALSE_ALIASES = {"错", "错误", "FALSE", "F", "NO", "N", "B", "×", "❌", "✘", "X"}


def normalize_answer(answer: str) -> str:
    return "".join(str(answer or "").strip().upper().split())


def normalize_multi_answer(answer: str) -> str:
    letters = re.findall(r"[A-Z]", normalize_answer(answer))
    if not letters:
        return normalize_answer(answer)
    return "".join(sorted(set(letters)))


def normalize_judge_answer(answer: str) -> str:
    compact = normalize_answer(answer)
    if compact in JUDGE_TRUE_ALIASES:
        return "T"
    if compact in JUDGE_FALSE_ALIASES:
        return "F"
    return compact


def normalize_question_type(question_type: str) -> str:
    normalized = str(question_type or "").strip()
    return normalized if normalized in VALID_QUESTION_TYPES else "single"


def normalize_standard_answer(question_type: str, answer: str) -> str:
    normalized_type = normalize_question_type(question_type)
    raw = str(answer or "").strip()
    if normalized_type == "multi":
        return normalize_multi_answer(raw)
    if normalized_type == "single":
        match = re.search(r"[A-Z]", raw.upper())
        return match.group(0) if match else normalize_answer(raw)
    if normalized_type == "judge":
        return normalize_judge_answer(raw)
    return raw


def is_answer_correct(question_type: str, user_answer: str, correct_answer: str) -> bool:
    normalized_type = normalize_question_type(question_type)
    return normalize_standard_answer(normalized_type, user_answer) == normalize_standard_answer(normalized_type, correct_answer)
