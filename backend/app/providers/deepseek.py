"""DeepSeek Provider：完全兼容 OpenAI 协议，仅固定默认 Base URL。"""
from __future__ import annotations

from app.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    provider_type = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"

    # DeepSeek 常用模型（仅用于前端下拉提示，真实能力以接口返回为准）
    KNOWN_MODELS = [
        "deepseek-chat",
        "deepseek-reasoner",
    ]
