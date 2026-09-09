"""OpenAI 兼容协议适配器。

支持任意兼容 /chat/completions 的服务（OpenAI / DeepSeek / 智谱 / 通义 / Moonshot…），
通过环境变量切换 base_url 与 key。结构化输出统一走 response_format=json_object +
Prompt 内嵌 schema（兼容性最广），后端再做字段级规整与兜底。
"""
from __future__ import annotations

import httpx

from .. import config
from ..prompts.loader import render as render_prompt
from ..schemas import schema_json_text, schema_text
from .base import Provider, ProviderError


class OpenAICompatibleProvider(Provider):
    name = "openai_compatible"

    def __init__(self) -> None:
        if not config.API_KEY:
            raise ProviderError("未配置 OPENAI_API_KEY / AI_API_KEY")
        self.api_key = config.API_KEY
        self.base_url = config.BASE_URL
        self._http = httpx.Client(timeout=config.HTTP_TIMEOUT)

    def chat_json(self, schema_key: str, messages: list[dict], temperature: float = 0.4) -> dict:
        return self._complete(schema_key, messages, temperature, want_json=True)

    def chat(self, messages: list[dict], temperature: float = 0.6) -> str:
        data = self._complete_raw(messages, temperature, want_json=False)
        return data  # type: ignore[return-value]

    # ---------- 内部 ----------
    def _system_plus(self, messages: list[dict]) -> list[dict]:
        system = render_prompt("system.txt")
        return [{"role": "system", "content": system}] + list(messages)

    def _complete(self, schema_key: str, messages: list[dict], temperature: float, want_json: bool) -> dict:
        last_err: Exception | None = None
        for attempt in range(2):  # 一次重试
            try:
                raw = self._complete_raw(messages, temperature, want_json, schema_key=schema_key)
                if want_json:
                    parsed = Provider.safe_json_loads(raw, schema_key)
                    # 空结构视为失败，触发重试
                    if self._looks_empty(parsed, schema_key):
                        raise ProviderError("模型返回空结构，重试")
                    return parsed
                return raw  # type: ignore[return-value]
            except ProviderError as e:  # 仅在重试后抛，避免掩盖
                last_err = e
        raise ProviderError(f"结构化输出请求失败: {last_err}")

    def _complete_raw(self, messages: list[dict], temperature: float,
                      want_json: bool, schema_key: str | None = None) -> str:
        body: dict = {
            "model": config.VISION_MODEL if self._is_vision(schema_key, messages) else config.TEXT_MODEL,
            "messages": self._system_plus(messages),
            "temperature": temperature,
        }
        if want_json and schema_key:
            # 结构化输出：schema 说明与结构示例已由各生成器注入提示词，
            # 这里只声明响应格式。切勿改写用户消息——
            # 多模态调用（含图片 base64）的 content 是数组，覆写成文本会丢图，
            # 导致模型认为"未提供图片"。
            body["response_format"] = {"type": "json_object"}
        try:
            resp = self._http.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"] or ""
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"模型接口返回 {e.response.status_code}: {e.response.text[:300]}") from e
        except (httpx.HTTPError, KeyError, IndexError) as e:
            raise ProviderError(f"模型接口调用失败: {e}") from e

    @staticmethod
    def _is_vision(schema_key: str | None, messages: list[dict]) -> bool:
        if schema_key == "product_analysis":
            return True
        # 视觉分析消息中包含 image_url
        if schema_key is None:
            for m in messages:
                c = m.get("content")
                if isinstance(c, list) and any(isinstance(p, dict) and p.get("type") == "image_url" for p in c):
                    return True
        return False

    @staticmethod
    def _looks_empty(parsed: dict, schema_key: str) -> bool:
        # 简单判空：核心字段均无值视为空
        checks = {
            "product_analysis": not parsed.get("product_name") and not parsed.get("category"),
            "titles": not parsed.get("taobao", {}).get("title"),
            "selling_points": not parsed.get("items"),
            "detail_sections": not parsed.get("sections"),
            "video_script": not parsed.get("hook") and not parsed.get("scenes"),
            "image_plans": not parsed.get("plans"),
        }
        return checks.get(schema_key, False)
