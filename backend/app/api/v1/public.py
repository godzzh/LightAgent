"""对外 API（已发布应用）：独立鉴权，不暴露内部管理接口。"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.response import EnvelopeRoute
from app.core.security import hash_api_key
from app.models.application import ApiKey, Application
from app.models.base import utcnow
from app.services.agent.service import chat_once, stream_chat
from app.services.workflow.service import run_workflow, stream_workflow
from app.utils.sse import sse_response

router = APIRouter(route_class=EnvelopeRoute, prefix="/open", tags=["对外 API"])


class OpenChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = None
    stream: bool = False


class OpenWorkflowRequest(BaseModel):
    inputs: dict = Field(default_factory=dict)


def _extract_key(request: Request, authorization: Optional[str], x_api_key: Optional[str]) -> str:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise UnauthorizedError("缺少 API Key（请在请求头传 Authorization: Bearer <key> 或 X-API-Key）")


async def _auth_app(
    app_id: str,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Application:
    raw = _extract_key(request, authorization, x_api_key)
    digest = hash_api_key(raw)
    key = (
        await db.execute(select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.enabled.is_(True)))
    ).scalar_one_or_none()
    if not key:
        raise UnauthorizedError("API Key 无效")
    if key.application_id != app_id:
        raise ForbiddenError("API Key 与应用不匹配")

    app = await db.get(Application, app_id)
    if not app:
        raise NotFoundError("应用不存在")
    if not app.api_enabled or app.status != "published":
        raise ForbiddenError("应用未发布或 API 访问未开启")

    key.last_used_at = utcnow()
    await db.commit()
    return app


@router.post("/{app_id}/chat-messages", summary="调用已发布 Agent（流式/非流式）")
async def open_chat(
    app_id: str,
    payload: OpenChatRequest,
    app: Application = Depends(_auth_app),
):
    session_id = payload.session_id or uuid.uuid4().hex
    if app.app_type == "workflow":
        raise ForbiddenError("该应用是工作流类型，请调用 /run 接口")

    if payload.stream:
        return sse_response(
            stream_chat(
                application_id=app.id, query=payload.query, session_id=session_id, source="api"
            )
        )
    result = await chat_once(
        application_id=app.id, query=payload.query, session_id=session_id, source="api"
    )
    return {
        "run_id": result.get("run_id"),
        "session_id": session_id,
        "answer": result.get("output", ""),
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms", 0),
    }


@router.post("/{app_id}/run", summary="调用已发布工作流应用")
async def open_run(
    app_id: str,
    payload: OpenWorkflowRequest,
    app: Application = Depends(_auth_app),
):
    if not app.workflow_id:
        raise ForbiddenError("该应用未绑定工作流")
    result = await run_workflow(
        workflow_id=app.workflow_id, inputs=payload.inputs, application_id=app.id, source="api"
    )
    return {
        "run_id": result.get("run_id"),
        "outputs": result.get("outputs", {}),
        "usage": result.get("usage", {}),
        "duration_ms": result.get("duration_ms", 0),
    }


@router.get("/{app_id}/info", summary="应用公开信息（欢迎语、开场问题）")
async def open_info(app_id: str, app: Application = Depends(_auth_app)):
    cfg = app.config or {}
    return {
        "id": app.id,
        "name": app.name,
        "description": app.description,
        "icon": app.icon,
        "app_type": app.app_type,
        "welcome_message": cfg.get("welcome_message", ""),
        "opening_questions": cfg.get("opening_questions", []),
    }
