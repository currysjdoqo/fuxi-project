"""
DeepSeek AI 服务模块
"""

import httpx
from typing import Optional

from routers.settings import _get_deepseek_api_key


# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"


def has_api_key() -> bool:
    """检查是否配置了 API Key"""
    key = _get_deepseek_api_key()
    return key is not None and len(key) > 0


async def get_ai_explanation(
    question_content: str,
    question_type: str,
    options: dict = None,
    user_answer: str = None,
    correct_answer: str = None,
    subject_name: str = None
) -> str:
    """
    调用 DeepSeek API 获取题目讲解

    Args:
        question_content: 题目内容
        question_type: 题目类型
        options: 选项（如果是选择题）
        user_answer: 用户的答案
        correct_answer: 正确答案
        subject_name: 科目名称

    Returns:
        AI 生成的讲解内容
    """
    api_key = _get_deepseek_api_key()

    if not api_key:
        return "⚠️ 尚未配置 DeepSeek API Key，请在设置页面配置后重试。"

    # 构建题目信息
    type_labels = {
        'single': '单选题',
        'multiple': '多选题',
        'judge': '判断题',
        'fill': '填空题',
        'short_answer': '简答题',
        'programming': '编程题'
    }
    type_name = type_labels.get(question_type, question_type)

    # 构建题目描述
    question_desc = f"【{type_name}】\n{question_content}\n"

    if options:
        if isinstance(options, dict):
            for key in sorted(options.keys()):
                question_desc += f"{key}. {options[key]}\n"
        elif isinstance(options, list):
            for opt in options:
                if isinstance(opt, dict):
                    question_desc += f"{opt.get('key', '')}. {opt.get('value', '')}\n"

    # 构建用户答案信息
    answer_info = ""
    if user_answer:
        answer_info += f"\n用户答案：{user_answer}"
    if correct_answer:
        answer_info += f"\n正确答案：{correct_answer}"

    # 构建选项文本
    options_text = ""
    if options:
        if isinstance(options, dict):
            for key in sorted(options.keys()):
                options_text += f"{key}. {options[key]}\n"
        elif isinstance(options, list):
            for opt in options:
                if isinstance(opt, dict):
                    options_text += f"{opt.get('key', '')}. {opt.get('value', '')}\n"

    # 构建 Prompt
    prompt = f"""请作为辅导老师，简洁讲解这道题，帮助学生快速理解。

题目：{question_content}
{f'选项：\n{options_text}' if options_text else ''}
正确答案：{correct_answer}

要求：
1. 答案解析：一句话说清为什么选这个答案（不超过50字）
2. 易错点：指出容易选错的原因（不超过30字）
3. 知识点：1-2个核心知识点（简短）
4. 语言要精炼，不要冗长，适合快速复习。"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.5,
                    "max_tokens": 800
                }
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            elif response.status_code == 401:
                return "⚠️ API Key 无效或已过期，请检查设置中的 DeepSeek API Key。"
            elif response.status_code == 429:
                return "⚠️ API 调用次数已达上限，请稍后再试。"
            else:
                return f"⚠️ API 调用失败（错误码：{response.status_code}），请稍后重试。"

    except httpx.ConnectError:
        return "⚠️ 无法连接到 DeepSeek API，请检查网络连接。"
    except httpx.TimeoutException:
        return "⚠️ API 请求超时，请稍后重试。"
    except Exception as e:
        return f"⚠️ 发生未知错误：{str(e)}"
