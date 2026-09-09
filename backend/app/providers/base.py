"""模型供应商抽象：所有上游环节只依赖 chat_json / chat，不关心供应商差异。"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from ..schemas import merge_and_normalize


class ProviderError(Exception):
    pass


class Provider(ABC):
    name = "base"

    @abstractmethod
    def chat_json(self, schema_key: str, messages: list[dict], temperature: float = 0.4) -> dict:
        """请求模型并返回符合 schema_key 结构的 dict。实现方负责 retry/降级。

        messages: 标准 OpenAI messages；图片用多模态 content parts。
        """

    def chat(self, messages: list[dict], temperature: float = 0.6) -> str:
        """普通文本对话（兜底用途）。"""
        raise ProviderError(f"provider {self.name} 不支持 chat")

    # 对"输出 must be json"的共性兜底
    @staticmethod
    def safe_json_loads(text: str, schema_key: str) -> dict:
        raw: Any = None
        try:
            raw = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            # 去除 ```json ... ``` 与前后噪音后重试
            cleaned = re.sub(r"```(?:json)?|```", "", text or "").strip()
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start >= 0 and end > start:
                try:
                    raw = json.loads(cleaned[start:end + 1])
                except json.JSONDecodeError:
                    raw = None
        return merge_and_normalize(schema_key, raw)
