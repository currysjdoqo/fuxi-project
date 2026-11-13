import asyncio

from utils.ai_import import sanitize_ai_questions
from utils import ai_import


def test_sanitize_ai_questions_filters_invalid_items() -> None:
    questions, errors = sanitize_ai_questions(
        {
            "questions": [
                {
                    "type": "single",
                    "content": "Python 属于哪种语言？",
                    "options": {"A": "编译型", "B": "解释型"},
                    "answer": "B",
                    "explanation": "",
                },
                {
                    "type": "judge",
                    "content": "",
                    "options": {},
                    "answer": "T",
                    "explanation": "",
                },
            ]
        }
    )

    assert len(questions) == 1
    assert questions[0]["type"] == "single"
    assert errors == ["第 2 题缺少题干"]


def test_parse_questions_with_ai_parses_json_payload(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"questions":[{"type":"single","content":"1+1=?","options":{"A":"1","B":"2"},"answer":"B","explanation":""}]}'
                        }
                    }
                ]
            }

    async def fake_post_chat(*args, **kwargs):
        assert args[1] == "test-key"
        return FakeResponse()

    monkeypatch.setattr(ai_import, "post_chat", fake_post_chat)
    questions, errors = asyncio.run(
        ai_import.parse_questions_with_ai("题目文本", "demo.txt", api_key="test-key")
    )

    assert not errors
    assert len(questions) == 1
    assert questions[0]["answer"] == "B"


def test_extract_text_for_ai_fallback_supports_csv() -> None:
    text = ai_import.extract_text_for_ai_fallback("demo.csv", "type,content,answer\nsingle,2+2=?,B".encode("utf-8"))
    assert "2+2=?" in text


if __name__ == "__main__":
    test_sanitize_ai_questions_filters_invalid_items()
    test_parse_questions_with_ai_parses_json_payload()
    test_extract_text_for_ai_fallback_supports_csv()
    print("ai import fallback checks passed")
