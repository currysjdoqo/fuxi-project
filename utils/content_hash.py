"""题目内容归一化与哈希，用于导入去重（避免整库正文进内存）。"""
from __future__ import annotations

import hashlib


def normalize_content(content: str) -> str:
    """去掉所有空白并转小写，作为判重基准。"""
    return "".join((content or "").lower().split())


def content_hash(content: str) -> str:
    return hashlib.sha256(normalize_content(content).encode("utf-8")).hexdigest()
