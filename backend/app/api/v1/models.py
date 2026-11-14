"""模型管理接口：供应商 CRUD、模型配置 CRUD、连接测试。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.core.response import EnvelopeRoute
from app.models.model_provider import ModelConfig, ModelProvider
from app.models.user import User
from app.providers.registry import PROVIDER_CLASSES, PROVIDER_PRESETS, build_provider
from app.schemas.model import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ProviderCreate,
    ProviderUpdate,
    TestConnectionRequest,
)

router = APIRouter(route_class=EnvelopeRoute, prefix="/models", tags=["模型管理"])


def _provider_out(p: ModelProvider, with_configs: bool = False) -> dict:
    data = {
        "id": p.id,
        "name": p.name,
        "provider_type": p.provider_type,
        "base_url": p.base_url,
        "api_key_masked": mask_secret(p.api_key_encrypted),
        "has_api_key": bool(p.api_key_encrypted),
        "enabled": p.enabled,
        "is_default": p.is_default,
        "remark": p.remark,
        "created_at": p.created_at,
    }
    if with_configs:
        data["configs"] = [_config_out(c) for c in p.configs]
    return data


def _config_out(c: ModelConfig) -> dict:
    return {
        "id": c.id,
        "provider_id": c.provider_id,
        "display_name": c.display_name,
        "model_name": c.model_name,
        "model_type": c.model_type,
        "temperature": c.temperature,
        "top_p": c.top_p,
        "max_tokens": c.max_tokens,
        "context_window": c.context_window,
        "supports_streaming": c.supports_streaming,
        "supports_tool_call": c.supports_tool_call,
        "is_default": c.is_default,
        "enabled": c.enabled,
        "remark": c.remark,
        "created_at": c.created_at,
    }


# ------------------------------------------------------------------ presets
@router.get("/presets", summary="供应商预设")
async def presets(user: User = Depends(get_current_user)):
    return PROVIDER_PRESETS


# ---------------------------------------------------------------- providers
@router.get("/providers", summary="供应商列表")
async def list_providers(
    with_configs: bool = True,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(ModelProvider).order_by(ModelProvider.created_at.asc()))).scalars().all()
    return [_provider_out(p, with_configs) for p in rows]


@router.post("/providers", summary="新增供应商")
async def create_provider(
    payload: ProviderCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if payload.provider_type not in PROVIDER_CLASSES:
        raise ValidationFailedError(f"不支持的供应商类型: {payload.provider_type}")
    provider = ModelProvider(
        name=payload.name,
        provider_type=payload.provider_type,
        base_url=payload.base_url,
        api_key_encrypted=encrypt_secret(payload.api_key),
        enabled=payload.enabled,
        is_default=payload.is_default,
        remark=payload.remark,
    )
    if payload.is_default:
        for p in (await db.execute(select(ModelProvider))).scalars().all():
            p.is_default = False
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return _provider_out(provider)


@router.patch("/providers/{provider_id}", summary="更新供应商")
async def update_provider(
    provider_id: str,
    payload: ProviderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(ModelProvider, provider_id)
    if not provider:
        raise NotFoundError("供应商不存在")
    if payload.name is not None:
        provider.name = payload.name
    if payload.base_url is not None:
        provider.base_url = payload.base_url
    if payload.api_key:
        provider.api_key_encrypted = encrypt_secret(payload.api_key)
    if payload.enabled is not None:
        provider.enabled = payload.enabled
    if payload.remark is not None:
        provider.remark = payload.remark
    if payload.is_default:
        for p in (await db.execute(select(ModelProvider))).scalars().all():
            p.is_default = p.id == provider.id
    await db.commit()
    await db.refresh(provider)
    return _provider_out(provider)


@router.delete("/providers/{provider_id}", summary="删除供应商")
async def delete_provider(
    provider_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    provider = await db.get(ModelProvider, provider_id)
    if not provider:
        raise NotFoundError("供应商不存在")
    await db.delete(provider)
    await db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ configs
@router.get("/configs", summary="模型配置列表")
async def list_configs(
    model_type: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ModelConfig).order_by(ModelConfig.created_at.asc())
    if model_type:
        stmt = stmt.where(ModelConfig.model_type == model_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [_config_out(c) for c in rows]


@router.post("/configs", summary="新增模型配置")
async def create_config(
    payload: ModelConfigCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(ModelProvider, payload.provider_id)
    if not provider:
        raise NotFoundError("供应商不存在")
    dup = (
        await db.execute(
            select(ModelConfig).where(
                ModelConfig.provider_id == payload.provider_id,
                ModelConfig.model_name == payload.model_name,
            )
        )
    ).scalar_one_or_none()
    if dup:
        raise ConflictError("该供应商下已存在同名模型")

    cfg = ModelConfig(**payload.model_dump())
    if payload.is_default:
        for c in (await db.execute(select(ModelConfig))).scalars().all():
            c.is_default = False
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return _config_out(cfg)


@router.patch("/configs/{config_id}", summary="更新模型配置")
async def update_config(
    config_id: str,
    payload: ModelConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = await db.get(ModelConfig, config_id)
    if not cfg:
        raise NotFoundError("模型配置不存在")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default"):
        for c in (await db.execute(select(ModelConfig))).scalars().all():
            c.is_default = c.id == cfg.id
    data.pop("is_default", None)
    for k, v in data.items():
        if v is not None:
            setattr(cfg, k, v)
    await db.commit()
    await db.refresh(cfg)
    return _config_out(cfg)


@router.delete("/configs/{config_id}", summary="删除模型配置")
async def delete_config(
    config_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    cfg = await db.get(ModelConfig, config_id)
    if not cfg:
        raise NotFoundError("模型配置不存在")
    await db.delete(cfg)
    await db.commit()
    return {"ok": True}


# --------------------------------------------------------------- test / list
@router.post("/test", summary="测试模型连接")
async def test_connection(
    payload: TestConnectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider_row = await db.get(ModelProvider, payload.provider_id) if payload.provider_id else None
    provider_type = payload.provider_type or (provider_row.provider_type if provider_row else "deepseek")
    base_url = payload.base_url or (provider_row.base_url if provider_row else "")
    api_key = payload.api_key or (decrypt_secret(provider_row.api_key_encrypted) if provider_row else "")

    if not api_key:
        raise ValidationFailedError("请提供 API Key")

    cls = PROVIDER_CLASSES.get(provider_type)
    if not cls:
        raise ValidationFailedError(f"不支持的供应商类型: {provider_type}")
    provider = cls(base_url=base_url or getattr(cls, "default_base_url", ""), api_key=api_key)
    ok_flag, message = await provider.validate_connection()

    models = await provider.get_models() if ok_flag else []
    return {"ok": ok_flag, "message": message, "models": models}


@router.get("/available", summary="可用模型（供应用绑定）")
async def available_models(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(ModelConfig, ModelProvider.name)
            .join(ModelProvider, ModelProvider.id == ModelConfig.provider_id)
            .where(ModelConfig.enabled.is_(True), ModelProvider.enabled.is_(True))
            .order_by(ModelConfig.model_type.asc(), ModelConfig.is_default.desc())
        )
    ).all()
    return [
        {**_config_out(cfg), "provider_name": pname}
        for cfg, pname in rows
    ]
