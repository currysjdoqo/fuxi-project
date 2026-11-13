"""DeepSeek API 共享 HTTP 客户端：复用连接池、限制并发、统一超时。"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"
# 图片识别走的视觉模型，可用环境变量覆盖
AI_VISION_MODEL = os.getenv("AI_VISION_MODEL", "deepseek-v2-chat")

# 连接池上限
MAX_CONNECTIONS = 20
MAX_KEEPALIVE_CONNECTIONS = 10
# 同时在飞的 AI 请求上限（避免一次性打爆上游限流）
MAX_CONCURRENT_REQUESTS = 4

_client: httpx.AsyncClient | None = None
_semaphore: asyncio.Semaphore | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=MAX_CONNECTIONS,
                max_keepalive_connections=MAX_KEEPALIVE_CONNECTIONS,
            ),
        )
    return _client


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    return _semaphore


async def post_chat(
    payload: dict[str, Any],
    api_key: str,
    timeout: float | None = None,
) -> httpx.Response:
    """复用同一个 AsyncClient 调用 DeepSeek，连接池让连续请求免去重复 TLS 握手。"""
    kwargs: dict[str, Any] = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    async with _get_semaphore():
        return await _get_client().post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            **kwargs,
        )


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
