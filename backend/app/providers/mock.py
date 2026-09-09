"""Mock 引擎：演示模式下按内置示例报告给出与真实模型同构的结构化结果。

真实生成与 Mock 生成的唯一区别是数据来源（Prompt 推理 vs 内置专家预写），
统一接口层让整条流水线（进度/报告/导出）不感知差异 —— 这是架构可插拔的证明点。
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from .base import Provider, ProviderError


class MockProvider(Provider):
    name = "mock"

    # 当前任务上下文：由 services 在开始流水线前注入对应示例的预写结果
    _seed: dict = {}
    _seed_meta: dict = {}
    _lock = threading.Lock()

    def set_seed(self, seed: dict, meta: Optional[dict] = None) -> None:
        with self._lock:
            self._seed = seed or {}
            self._seed_meta = meta or {}

    def seed_snapshot(self) -> dict:
        return {**self._seed}

    def chat_json(self, schema_key: str, messages: list[dict], temperature: float = 0.4) -> dict:
        from ..schemas import SCHEMA_SPECS, merge_and_normalize

        mock_key = SCHEMA_SPECS[schema_key]["mock_key"]
        with self._lock:
            value = self._seed.get(mock_key)
        if value is None:
            # 理论上 mock 模式只接受示例任务，走到这里说明缺预写数据
            raise ProviderError(
                "Mock 引擎缺少该示例的预写数据；演示模式请使用内置示例，或配置 API Key 走真实模型。"
            )
        return merge_and_normalize(schema_key, value)
