"""Provider 工厂：根据数据库中的模型配置构造统一 Provider 实例。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.exceptions import AppError, NotFoundError
from app.models.model_provider import ModelConfig, ModelProvider
from app.providers.base import BaseLLMProvider
from app.providers.deepseek import DeepSeekProvider
from app.providers.openai_compatible import OpenAICompatibleProvider

PROVIDER_CLASSES: dict[str, type[BaseLLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "openai": OpenAICompatibleProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "qwen": OpenAICompatibleProvider,  # 预留：通义千问兼容模式
    "moonshot": OpenAICompatibleProvider,  # 预留
    "zhipu": OpenAICompatibleProvider,  # 预留
    "ollama": OpenAICompatibleProvider,  # 预留：本地 OpenAI 兼容网关
}

# 新建供应商时前端可选的预设
PROVIDER_PRESETS = [
    {"type": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1"},
    {"type": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1"},
    {"type": "openai_compatible", "name": "OpenAI 兼容接口", "base_url": ""},
    {"type": "qwen", "name": "通义千问（预留）", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"type": "moonshot", "name": "Moonshot（预留）", "base_url": "https://api.moonshot.cn/v1"},
    {"type": "zhipu", "name": "智谱 AI（预留）", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    {"type": "ollama", "name": "Ollama（预留）", "base_url": "http://localhost:11434/v1"},
]


def build_provider(provider: ModelProvider) -> BaseLLMProvider:
    cls = PROVIDER_CLASSES.get(provider.provider_type, OpenAICompatibleProvider)
    return cls(
        base_url=provider.base_url or getattr(cls, "default_base_url", ""),
        api_key=decrypt_secret(provider.api_key_encrypted),
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
    )


async def get_model_config(db: AsyncSession, model_config_id: Optional[str]) -> ModelConfig:
    """取模型配置；未指定时回退到默认模型。"""
    if model_config_id:
        cfg = await db.get(ModelConfig, model_config_id)
        if not cfg:
            raise NotFoundError("模型配置不存在")
        return cfg
    from sqlalchemy import select

    stmt = (
        select(ModelConfig)
        .where(ModelConfig.enabled.is_(True))
        .order_by(ModelConfig.is_default.desc(), ModelConfig.created_at.asc())
        .limit(1)
    )
    cfg = (await db.execute(stmt)).scalar_one_or_none()
    if not cfg:
        raise AppError("尚未配置可用模型，请先到「模型管理」添加模型")
    return cfg


async def build_provider_for_config(
    db: AsyncSession, model_config: ModelConfig
) -> BaseLLMProvider:
    provider = await db.get(ModelProvider, model_config.provider_id)
    if not provider:
        raise NotFoundError("模型供应商不存在")
    if not provider.enabled:
        raise AppError("模型供应商已被禁用")
    return build_provider(provider)
