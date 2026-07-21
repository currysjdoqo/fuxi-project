"""
DeepSeek AI client.
"""

from __future__ import annotations

import httpx

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"


def has_api_key(api_key: str | None = None) -> bool:
    return bool(api_key)


async def get_ai_explanation(
    question_content: str,
    question_type: str,
    options: dict | None = None,
    user_answer: str | None = None,
    correct_answer: str | None = None,
    subject_name: str | None = None,
    api_key: str | None = None,
) -> str:
    key = api_key
    if not key:
        return "尚未配置个人 DeepSeek API Key"

    type_labels = {
        "single": "单选题",
        "multiple": "多选题",
        "judge": "判断题",
        "fill": "填空题",
        "short_answer": "简答题",
        "programming": "编程题",
    }
    type_name = type_labels.get(question_type, question_type)

    options_text = ""
    if options:
        if isinstance(options, dict):
            for k in sorted(options.keys()):
                options_text += f"{k}. {options[k]}\n"
        elif isinstance(options, list):
            for opt in options:
                if isinstance(opt, dict):
                    options_text += f"{opt.get('key', '')}. {opt.get('value', '')}\n"

    options_section = f"选项：\n{options_text}" if options_text else ""
    prompt = f"""请作为辅导老师，简洁讲解这道题，帮助学生快速理解。
题目类型：{type_name}
题目：{question_content}
{options_section}
正确答案：{correct_answer or ''}
学科：{subject_name or ''}
要求：1. 解释要简短直接 2. 指出易错点 3. 不要编造题目外内容
"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 800,
                },
            )
    except httpx.ConnectError:
        return "无法连接 DeepSeek API"
    except httpx.TimeoutException:
        return "DeepSeek 请求超时"
    except Exception as exc:
        return f"DeepSeek 请求失败: {exc}"

    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    if response.status_code == 401:
        return "DeepSeek API Key 无效或已过期"
    if response.status_code == 429:
        return "DeepSeek 调用次数过多，请稍后重试"
    return f"DeepSeek 调用失败: HTTP {response.status_code}"
