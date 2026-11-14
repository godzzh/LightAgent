"""应用管理接口：CRUD / 复制 / 发布 / 版本 / API Key。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import Pagination, get_current_user, paginate
from app.core.exceptions import ConflictError, NotFoundError
from app.core.response import EnvelopeRoute
from app.core.security import generate_api_key
from app.models.application import ApiKey, Application, ApplicationVersion
from app.models.base import utcnow
from app.models.run import AgentRun
from app.models.user import User
from app.schemas.application import (
    AgentConfig,
    ApplicationCreate,
    ApplicationUpdate,
    PublishRequest,
)
from app.services.workspace_service import get_user_workspace

router = APIRouter(route_class=EnvelopeRoute, prefix="/applications", tags=["应用管理"])

TEMPLATES = [
    {
        "key": "blank",
        "name": "空白 Agent",
        "app_type": "chat_agent",
        "description": "从零配置一个智能体",
        "config": {},
    },
    {
        "key": "customer_service",
        "name": "客服助手",
        "app_type": "chat_agent",
        "description": "基于知识库回答用户问题，并给出引用来源",
        "config": {
            "system_prompt": (
                "你是一名专业、耐心的客服助手。\n"
                "请优先依据下面的知识库内容回答用户问题：\n\n{{knowledge_context}}\n\n"
                "要求：\n1. 只依据已知信息回答，不要编造；\n2. 资料中没有的内容，明确告知用户并提供可行建议；\n"
                "3. 回答简洁、分点，必要时给出处。"
            ),
            "welcome_message": "你好，我是客服助手，请描述你遇到的问题。",
            "opening_questions": ["产品如何退换货？", "支持哪些支付方式？"],
            "enable_knowledge": True,
            "enable_tools": False,
        },
    },
    {
        "key": "data_analyst",
        "name": "数据助手",
        "app_type": "chat_agent",
        "description": "可调用计算与 HTTP 工具完成数据查询与计算",
        "config": {
            "system_prompt": "你是一名数据分析助手，善于使用工具完成计算与数据查询。回答时先说明结论，再给出关键依据。",
            "mode": "function_calling",
            "enable_tools": True,
            "enable_knowledge": False,
            "tools": [
                {"tool_key": "math_calc", "enabled": True},
                {"tool_key": "current_time", "enabled": True},
                {"tool_key": "http_request", "enabled": True},
            ],
        },
    },
    {
        "key": "workflow_blank",
        "name": "空白工作流应用",
        "app_type": "workflow",
        "description": "通过可视化工作流编排业务逻辑",
        "config": {},
    },
]


def _app_out(a: Application, extra: Optional[dict] = None) -> dict:
    data = {
        "id": a.id,
        "workspace_id": a.workspace_id,
        "name": a.name,
        "description": a.description,
        "icon": a.icon,
        "app_type": a.app_type,
        "status": a.status,
        "config": a.config or {},
        "model_config_id": a.model_config_id,
        "workflow_id": a.workflow_id,
        "api_enabled": a.api_enabled,
        "run_count": a.run_count,
        "published_at": a.published_at,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }
    if extra:
        data.update(extra)
    return data


@router.get("/templates", summary="应用模板")
async def list_templates(user: User = Depends(get_current_user)):
    return TEMPLATES


@router.get("", summary="应用列表")
async def list_applications(
    keyword: str = "",
    app_type: Optional[str] = None,
    status: Optional[str] = None,
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_user_workspace(db, user)
    stmt = select(Application).where(Application.workspace_id == ws.id)
    count_stmt = select(func.count(Application.id)).where(Application.workspace_id == ws.id)
    if keyword:
        stmt = stmt.where(Application.name.contains(keyword))
        count_stmt = count_stmt.where(Application.name.contains(keyword))
    if app_type:
        stmt = stmt.where(Application.app_type == app_type)
        count_stmt = count_stmt.where(Application.app_type == app_type)
    if status:
        stmt = stmt.where(Application.status == status)
        count_stmt = count_stmt.where(Application.status == status)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Application.updated_at.desc()).offset(p.offset).limit(p.page_size)
        )
    ).scalars().all()
    return paginate([_app_out(a) for a in rows], int(total), p)


@router.post("", summary="创建应用")
async def create_application(
    payload: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_user_workspace(db, user)
    config = dict(payload.config or {})
    if payload.template:
        tpl = next((t for t in TEMPLATES if t["key"] == payload.template), None)
        if tpl:
            merged = dict(tpl["config"])
            merged.update(config)
            config = merged
    AgentConfig(**config)  # 校验结构，非法配置直接报错

    app = Application(
        workspace_id=ws.id,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        app_type=payload.app_type,
        config=config,
        model_config_id=payload.model_config_id or config.get("model_config_id"),
        workflow_id=payload.workflow_id,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return _app_out(app)


@router.get("/{application_id}", summary="应用详情")
async def get_application(
    application_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    return _app_out(app)


@router.patch("/{application_id}", summary="更新应用")
async def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    if payload.name is not None:
        app.name = payload.name
    if payload.description is not None:
        app.description = payload.description
    if payload.icon is not None:
        app.icon = payload.icon
    if payload.config is not None:
        AgentConfig(**payload.config)
        app.config = payload.config
        if payload.config.get("model_config_id"):
            app.model_config_id = payload.config["model_config_id"]
    if payload.model_config_id is not None:
        app.model_config_id = payload.model_config_id
    if payload.workflow_id is not None:
        app.workflow_id = payload.workflow_id
    await db.commit()
    await db.refresh(app)
    return _app_out(app)


@router.delete("/{application_id}", summary="删除应用")
async def delete_application(
    application_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    await db.delete(app)
    await db.commit()
    return {"ok": True}


@router.post("/{application_id}/copy", summary="复制应用")
async def copy_application(
    application_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    new_app = Application(
        workspace_id=app.workspace_id,
        name=f"{app.name} 副本",
        description=app.description,
        icon=app.icon,
        app_type=app.app_type,
        config=app.config,
        model_config_id=app.model_config_id,
        workflow_id=app.workflow_id,
    )
    db.add(new_app)
    await db.commit()
    await db.refresh(new_app)
    return _app_out(new_app)


@router.post("/{application_id}/publish", summary="发布应用")
async def publish_application(
    application_id: str,
    payload: PublishRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")

    last_version = (
        await db.execute(
            select(func.max(ApplicationVersion.version)).where(
                ApplicationVersion.application_id == app.id
            )
        )
    ).scalar_one() or 0
    version = ApplicationVersion(
        application_id=app.id,
        version=int(last_version) + 1,
        config=app.config or {},
        note="发布快照",
    )
    db.add(version)

    app.status = "published"
    app.api_enabled = bool(payload.api_enabled)
    app.published_at = utcnow()

    plain_key = None
    if payload.create_key:
        exists = (
            await db.execute(select(ApiKey).where(ApiKey.application_id == app.id).limit(1))
        ).scalar_one_or_none()
        if not exists:
            raw, prefix, digest = generate_api_key()
            db.add(
                ApiKey(application_id=app.id, name=payload.key_name, key_prefix=prefix, key_hash=digest)
            )
            plain_key = raw

    await db.commit()
    await db.refresh(app)
    return {
        "application": _app_out(app),
        "version": version.version,
        "api_key": plain_key,  # 仅在创建时返回一次
        "endpoint": f"/api/v1/open/{app.id}/chat-messages",
    }


@router.post("/{application_id}/unpublish", summary="取消发布")
async def unpublish_application(
    application_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    app.status = "draft"
    app.api_enabled = False
    await db.commit()
    return _app_out(app)


@router.get("/{application_id}/versions", summary="版本列表")
async def list_versions(
    application_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(ApplicationVersion)
            .where(ApplicationVersion.application_id == application_id)
            .order_by(ApplicationVersion.version.desc())
        )
    ).scalars().all()
    return [
        {"id": v.id, "version": v.version, "note": v.note, "created_at": v.created_at, "config": v.config}
        for v in rows
    ]


@router.get("/{application_id}/keys", summary="API Key 列表")
async def list_keys(
    application_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(ApiKey).where(ApiKey.application_id == application_id).order_by(ApiKey.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "enabled": k.enabled,
            "last_used_at": k.last_used_at,
            "created_at": k.created_at,
        }
        for k in rows
    ]


@router.post("/{application_id}/keys", summary="生成新的 API Key")
async def create_key(
    application_id: str,
    name: str = "default",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    raw, prefix, digest = generate_api_key()
    key = ApiKey(application_id=app.id, name=name, key_prefix=prefix, key_hash=digest)
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return {"id": key.id, "name": key.name, "api_key": raw, "key_prefix": prefix}


@router.delete("/{application_id}/keys/{key_id}", summary="删除 API Key")
async def delete_key(
    application_id: str,
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = await db.get(ApiKey, key_id)
    if not key or key.application_id != application_id:
        raise NotFoundError("API Key 不存在")
    await db.delete(key)
    await db.commit()
    return {"ok": True}


@router.get("/{application_id}/stats", summary="应用运行统计")
async def app_stats(
    application_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    total = (
        await db.execute(
            select(func.count(AgentRun.id)).where(AgentRun.application_id == application_id)
        )
    ).scalar_one()
    tokens = (
        await db.execute(
            select(func.coalesce(func.sum(AgentRun.total_tokens), 0)).where(
                AgentRun.application_id == application_id
            )
        )
    ).scalar_one()
    if not application_id:
        raise ConflictError("缺少应用 ID")
    return {"runs": int(total), "tokens": int(tokens)}
