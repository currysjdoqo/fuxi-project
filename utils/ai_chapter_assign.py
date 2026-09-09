"""AI 自动划分章节：调用 DeepSeek 为一批题目分配章节归属。"""

import json
import re
from typing import Any, Optional

import httpx

from utils.ai_import import DEEPSEEK_API_URL, DEEPSEEK_MODEL, _extract_json_payload

# 每批最多处理的题目数，控制 token 用量
BATCH_SIZE = 40
# 每题题干截取最大字符数，避免超长题干撑爆 token
CONTENT_PREVIEW_LEN = 120


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


def _build_prompt(
    questions: list[dict[str, Any]],
    existing_chapter_names: list[str],
    batch_offset: int,
) -> str:
    """构造 DeepSeek prompt。"""
    lines = []
    for i, q in enumerate(questions):
        global_index = batch_offset + i
        content = (q.get("content") or "").strip()[:CONTENT_PREVIEW_LEN]
        q_type = q.get("type", "single")
        lines.append(f"[{global_index}] ({q_type}) {content}")

    question_list = "\n".join(lines)

    existing_hint = ""
    if existing_chapter_names:
        existing_hint = f"\n已有章节名称（优先匹配这些章节）：\n{', '.join(existing_chapter_names)}"

    return f"""你是题库章节划分助手。请为下方每道题目判断它属于哪个章节。
{existing_hint}
规则：
1. 只能输出 JSON，不能输出任何额外解释。
2. 输出格式：{{"assignments": [{{"index": 题目序号, "chapter": "章节名称"}}]}}
3. 章节名称要简洁规范，如"第1章 绪论""第3章 决策树"。同一主题的题目归到同一章节。
4. 如果题目内容明显属于同一章节，务必使用相同的章节名称。
5. 如果已有章节列表，优先使用已有名称（可省略"第X章"前缀直接用主题名）。
6. index 必须与下方题目序号一一对应，不可遗漏。

题目列表：
{question_list}
"""


async def assign_chapters_with_ai(
    questions: list[dict[str, Any]],
    existing_chapter_names: Optional[list[str]] = None,
    api_key: Optional[str] = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    调用 DeepSeek 为一批题目划分章节。

    :param questions: 题目列表，每个题目至少包含 content 和 type
    :param existing_chapter_names: 已有章节名列表，AI 会优先匹配
    :param api_key: 用户的 DeepSeek API Key
    :return: (assignments, errors)
        assignments: [{"index": 0, "chapter": "第1章 绪论"}, ...]
        errors: 错误信息列表
    """
    if not api_key:
        return [], ["尚未配置个人 DeepSeek API Key"]

    if not questions:
        return [], ["没有可供划分章节的题目"]

    existing = existing_chapter_names or []
    all_assignments: list[dict[str, Any]] = []
    all_errors: list[str] = []

    # 分批处理
    for batch_start in range(0, len(questions), BATCH_SIZE):
        batch = questions[batch_start:batch_start + BATCH_SIZE]
        prompt = _build_prompt(batch, existing, batch_start)

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    DEEPSEEK_API_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": DEEPSEEK_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个只返回合法 JSON 的题库章节划分器。",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 4000,
                        "response_format": {"type": "json_object"},
                    },
                )
        except httpx.TimeoutException:
            all_errors.append(f"第 {batch_start + 1}-{batch_start + len(batch)} 题：AI 划分超时")
            continue
        except httpx.ConnectError:
            all_errors.append("无法连接 DeepSeek API，请检查网络")
            break
        except Exception as exc:
            all_errors.append(f"AI 划分请求失败: {exc}")
            continue

        if response.status_code == 401:
            all_errors.append("DeepSeek API Key 无效或已过期")
            break
        if response.status_code == 429:
            all_errors.append("DeepSeek API 调用次数过多，请稍后重试")
            break
        if response.status_code >= 400:
            all_errors.append(f"DeepSeek API 调用失败: HTTP {response.status_code}")
            continue

        try:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            payload = _extract_json_payload(content)
        except Exception as exc:
            all_errors.append(f"第 {batch_start + 1}-{batch_start + len(batch)} 题：AI 返回结果无法解析: {exc}")
            continue

        # 提取 assignments
        if isinstance(payload, dict):
            items = payload.get("assignments", [])
        elif isinstance(payload, list):
            items = payload
        else:
            all_errors.append(f"第 {batch_start + 1}-{batch_start + len(batch)} 题：AI 返回格式异常")
            continue

        if not isinstance(items, list):
            all_errors.append(f"第 {batch_start + 1}-{batch_start + len(batch)} 题：AI 返回的 assignments 不是数组")
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            idx = item.get("index")
            chapter = str(item.get("chapter", "")).strip()
            if idx is None or not chapter:
                continue
            all_assignments.append({"index": int(idx), "chapter": chapter})

    return all_assignments, all_errors
