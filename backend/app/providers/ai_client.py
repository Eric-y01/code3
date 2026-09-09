"""统一接口门面：业务代码只 import get_client() 即可调用，供应商切换零改动。"""
from __future__ import annotations

from .. import config
from .base import Provider
from .mock import MockProvider
from .openai_compat import OpenAICompatibleProvider

_client: Provider | None = None
_client_init_error: str | None = None


def get_client() -> Provider:
    global _client, _client_init_error
    if _client is None:
        if config.IS_MOCK:
            _client = MockProvider()
        else:
            try:
                _client = OpenAICompatibleProvider()
            except Exception as e:  # key 缺失等
                _client_init_error = str(e)
                _client = MockProvider()  # 兜底到 mock，保证服务不崩
    return _client


def active_name() -> str:
    return _client.name if _client is not None else config.PROVIDER


def init_error() -> str | None:
    return _client_init_error
