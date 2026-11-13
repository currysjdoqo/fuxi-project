"""AI 知识点提炼：为章节题目打标签、生成知识点总结和知识大纲。"""

import asyncio
from typing import Any, Optional

import httpx

from utils.ai_http import DEEPSEEK_MODEL, post_chat
from utils.ai_import import _extract_json_payload

# 每题题干截取最大字符数
CONTENT_PREVIEW_LEN = 150
# 标签批量处理每批最多题目数
TAG_BATCH_SIZE = 30
# 总结/大纲最多使用题目数（取前 N 题）
SUMMARY_MAX_QUESTIONS = 50


def _prepare_questions_for_ai(questions: list[dict[str, Any]], max_count: int = None) -> list[dict[str, Any]]:
    """提取题目的题干+答案+解析，截取长度。"""
    qs = questions[:max_count] if max_count else questions
    result = []
    for i, q in enumerate(qs):
        content = (q.get("content") or "").strip()[:CONTENT_PREVIEW_LEN]
        q_type = q.get("type", "single")
        answer = (q.get("answer") or "").strip()
        explanation = (q.get("explanation") or "").strip()[:100]
        result.append({"index": i, "type": q_type, "content": content, "answer": answer, "explanation": explanation})
    return result


async def _call_deepseek(prompt: str, system_content: str, api_key: str) -> tuple[Any, list[str]]:
    """调用 DeepSeek 并解析 JSON 返回。"""
    try:
        response = await post_chat(
            {
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"},
            },
            api_key,
            timeout=90.0,
        )
    except httpx.TimeoutException:
        return None, ["AI 提炼超时，请稍后重试"]
    except httpx.ConnectError:
        return None, ["无法连接 DeepSeek API，请检查网络"]
    except Exception as exc:
        return None, [f"AI 提炼请求失败: {exc}"]

    if response.status_code == 401:
        return None, ["DeepSeek API Key 无效或已过期"]
    if response.status_code == 429:
        return None, ["DeepSeek API 调用次数过多，请稍后重试"]
    if response.status_code >= 400:
        return None, [f"DeepSeek API 调用失败: HTTP {response.status_code}"]

    try:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        payload = _extract_json_payload(content)
        return payload, []
    except Exception as exc:
        return None, [f"AI 返回结果无法解析: {exc}"]


async def tag_questions_with_ai(
    questions: list[dict[str, Any]],
    api_key: Optional[str] = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    为一批题目打 1~3 个知识点标签。

    :return: (tags, errors)
        tags: [{"index": 0, "tags": ["梯度下降", "学习率"]}, ...]
    """
    if not api_key:
        return [], ["尚未配置个人 DeepSeek API Key"]

    if not questions:
        return [], ["没有可供打标签的题目"]

    all_tags: list[dict[str, Any]] = []
    all_errors: list[str] = []

    batches = [
        (batch_start, questions[batch_start:batch_start + TAG_BATCH_SIZE])
        for batch_start in range(0, len(questions), TAG_BATCH_SIZE)
    ]

    async def _tag_batch(batch_start: int, batch: list[dict[str, Any]]):
        prepared = _prepare_questions_for_ai(batch, TAG_BATCH_SIZE)

        prompt = f"""你是题库知识点标注助手。请为下方每道题目提取 1~3 个核心知识点标签。
要求：
1. 只能输出 JSON，不能输出任何额外解释。
2. 输出格式：{{"tags": [{{"index": 题目序号, "tags": ["标签1", "标签2"]}}]}}
3. index 必须与下方题目序号一一对应，不可遗漏。
4. 标签要简洁（2~6 个字），如"梯度下降""过拟合""信息增益"。
5. 每道题 1~3 个标签，不要过多。

题目列表（JSON）：
{__import__('json').dumps(prepared, ensure_ascii=False)}
"""
        payload, errors = await _call_deepseek(
            prompt, "你是一个只返回合法 JSON 的知识点标注器。", api_key,
        )
        return batch_start, batch, payload, errors

    # 各批题目相互独立，并发请求；真正的并发上限由 utils.ai_http 控制
    results = await asyncio.gather(*(_tag_batch(batch_start, batch) for batch_start, batch in batches))

    for batch_start, batch, payload, errors in results:
        if errors:
            all_errors.extend(errors)
            if "API Key" in errors[0]:
                break
            continue

        if isinstance(payload, dict):
            items = payload.get("tags", [])
        elif isinstance(payload, list):
            items = payload
        else:
            all_errors.append(f"第 {batch_start + 1}-{batch_start + len(batch)} 题：AI 返回格式异常")
            continue

        if not isinstance(items, list):
            all_errors.append(f"第 {batch_start + 1}-{batch_start + len(batch)} 题：AI 返回的 tags 不是数组")
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            idx = item.get("index")
            tags = item.get("tags", [])
            if idx is None or not isinstance(tags, list):
                continue
            tag_list = [str(t).strip() for t in tags if str(t).strip()][:3]
            all_tags.append({"index": int(idx), "tags": tag_list})

    return all_tags, all_errors


async def generate_summary_with_ai(
    questions: list[dict[str, Any]],
    chapter_name: str,
    api_key: Optional[str] = None,
) -> tuple[str, list[str]]:
    """
    基于本章题目生成 Markdown 知识点总结讲义。

    :return: (summary_md, errors)
    """
    if not api_key:
        return "", ["尚未配置个人 DeepSeek API Key"]

    if not questions:
        return "", ["该章节没有题目，无法生成总结"]

    prepared = _prepare_questions_for_ai(questions, SUMMARY_MAX_QUESTIONS)

    prompt = f"""你是复习资料编写助手。请根据下方章节「{chapter_name}」的题目，编写一份知识点复习总结。
要求：
1. 输出 Markdown 格式，包含以下部分：
   - **核心概念**：用简洁语言概括本章考查的核心知识点
   - **重要公式/结论**：列出本章涉及的关键公式或重要结论
   - **常见易错点**：根据题目特点，总结容易出错的地方
2. 不要输出 JSON，直接输出 Markdown 文本。
3. 控制在 800 字以内，聚焦核心。
4. 如果题目不足以支撑某部分（如没有公式），可省略该部分。

题目列表（JSON）：
{__import__('json').dumps(prepared, ensure_ascii=False)}
"""
    try:
        response = await post_chat(
            {
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个复习资料编写助手，输出 Markdown 格式的知识点总结。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 4000,
            },
            api_key,
            timeout=90.0,
        )
    except httpx.TimeoutException:
        return "", ["AI 生成总结超时，请稍后重试"]
    except httpx.ConnectError:
        return "", ["无法连接 DeepSeek API，请检查网络"]
    except Exception as exc:
        return "", [f"AI 生成总结请求失败: {exc}"]

    if response.status_code == 401:
        return "", ["DeepSeek API Key 无效或已过期"]
    if response.status_code == 429:
        return "", ["DeepSeek API 调用次数过多，请稍后重试"]
    if response.status_code >= 400:
        return "", [f"DeepSeek API 调用失败: HTTP {response.status_code}"]

    try:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        # 去掉可能的代码围栏
        text = content.strip()
        if text.startswith("```"):
            import re
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return text.strip(), []
    except Exception as exc:
        return "", [f"AI 返回结果无法解析: {exc}"]


async def generate_outline_with_ai(
    questions: list[dict[str, Any]],
    chapter_name: str,
    api_key: Optional[str] = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    生成章节知识大纲（树形结构 JSON）。

    :return: (outline, errors)
        outline: [{"title": "核心概念", "children": [{"title": "梯度下降"}, ...]}, ...]
    """
    if not api_key:
        return [], ["尚未配置个人 DeepSeek API Key"]

    if not questions:
        return [], ["该章节没有题目，无法生成大纲"]

    prepared = _prepare_questions_for_ai(questions, SUMMARY_MAX_QUESTIONS)

    prompt = f"""你是知识大纲生成助手。请根据下方章节「{chapter_name}」的题目，生成一份树形知识大纲。
要求：
1. 只能输出 JSON，不能输出任何额外解释。
2. 输出格式：{{"outline": [{{"title": "一级节点", "children": [{{"title": "二级节点", "children": []}}]}}]}}
3. 层级不超过 3 级。
4. 每个节点的 title 要简洁（2~8 个字）。
5. 根据题目内容归纳出 3~8 个一级节点。

题目列表（JSON）：
{__import__('json').dumps(prepared, ensure_ascii=False)}
"""
    payload, errors = await _call_deepseek(
        prompt, "你是一个只返回合法 JSON 的知识大纲生成器。", api_key,
    )
    if errors:
        return [], errors

    if isinstance(payload, dict):
        outline = payload.get("outline", [])
    elif isinstance(payload, list):
        outline = payload
    else:
        return [], ["AI 返回格式异常"]

    if not isinstance(outline, list):
        return [], ["AI 返回的 outline 不是数组"]

    return outline, []
