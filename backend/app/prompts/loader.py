"""Prompt 模板加载与渲染。

模板均为 .txt 独立文件，占位符使用 {{key}}（与 JSON 花括号天然不冲突）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from ..config import PROMPTS_DIR

_CACHE: dict[str, str] = {}


def _load(name: str) -> str:
    if name not in _CACHE:
        _CACHE[name] = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    return _CACHE[name]


def render(name: str, values: Mapping[str, Any] | None = None) -> str:
    text = _load(name)
    if not values:
        return text
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", str(val))
    # 移除未被填充的占位符，避免漏出 {{xxx}}
    text = re.sub(r"\{\{\s*[\w.]+\s*\}\}", "", text)
    return text


def template_file(name: str) -> Path:
    return PROMPTS_DIR / name
