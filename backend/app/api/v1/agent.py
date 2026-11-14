"""Agent 对话与调试接口（SSE 流式）。"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import Pagination, get_current_user, paginate
from app.core.exceptions import NotFoundError
from app.core.response import EnvelopeRoute
from app.models.application import Application, Conversation, Message
from app.models.run import AgentRun, AgentStep
from app.models.user import User
from app.schemas.application import ChatRequest
from app.services.agent.service import chat_once, stream_chat
from app.utils.sse import sse_response

router = APIRouter(route_class=EnvelopeRoute, prefix="/agent", tags=["Agent 调试"])


@router.post("/{application_id}/chat", summary="Agent 对话（stream=true 返回 SSE）")
async def agent_chat(
    application_id: str,
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    session_id = payload.session_id or uuid.uuid4().hex

    if payload.stream:
        return sse_response(
            stream_chat(
                application_id=application_id,
                query=payload.query,
                session_id=session_id,
                source="debug",
                user_id=user.id,
            )
        )

    result = await chat_once(
        application_id=application_id, query=payload.query, session_id=session_id, source="debug", user_id=user.id
    )
    return {**result, "session_id": session_id}


@router.get("/applications/{application_id}/conversations", summary="会话列表")
async def list_conversations(
    application_id: str,
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conversation).where(Conversation.application_id == application_id)
    total = (
        await db.execute(
            select(func.count(Conversation.id)).where(Conversation.application_id == application_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(stmt.order_by(Conversation.updated_at.desc()).offset(p.offset).limit(p.page_size))
    ).scalars().all()
    return paginate(
        [
            {
                "id": c.id,
                "session_id": c.session_id,
                "title": c.title,
                "source": c.source,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in rows
        ],
        int(total),
        p,
    )


@router.get("/conversations/{conversation_id}/messages", summary="会话消息")
async def conversation_messages(
    conversation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise NotFoundError("会话不存在")
    rows = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
    ).scalars().all()
    return {
        "conversation": {"id": conv.id, "title": conv.title, "session_id": conv.session_id},
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "prompt_tokens": m.prompt_tokens,
                "completion_tokens": m.completion_tokens,
                "created_at": m.created_at,
            }
            for m in rows
        ],
    }


@router.delete("/conversations/{conversation_id}", summary="删除会话")
async def delete_conversation(
    conversation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise NotFoundError("会话不存在")
    await db.delete(conv)
    await db.commit()
    return {"ok": True}


@router.get("/runs", summary="Agent 运行记录")
async def list_runs(
    application_id: Optional[str] = None,
    status: Optional[str] = None,
    keyword: str = "",
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AgentRun)
    count_stmt = select(func.count(AgentRun.id))
    if application_id:
        stmt = stmt.where(AgentRun.application_id == application_id)
        count_stmt = count_stmt.where(AgentRun.application_id == application_id)
    if status:
        stmt = stmt.where(AgentRun.status == status)
        count_stmt = count_stmt.where(AgentRun.status == status)
    if keyword:
        stmt = stmt.where(AgentRun.user_input.contains(keyword))
        count_stmt = count_stmt.where(AgentRun.user_input.contains(keyword))

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(AgentRun.created_at.desc()).offset(p.offset).limit(p.page_size))
    ).scalars().all()
    return paginate(
        [
            {
                "id": r.id,
                "application_id": r.application_id,
                "conversation_id": r.conversation_id,
                "status": r.status,
                "user_input": r.user_input[:200],
                "output": (r.output or "")[:200],
                "model_name": r.model_name,
                "mode": r.mode,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "tool_calls": r.tool_calls,
                "duration_ms": r.duration_ms,
                "error": r.error,
                "created_at": r.created_at,
                "source": r.source,
            }
            for r in rows
        ],
        int(total),
        p,
    )


@router.get("/runs/{run_id}", summary="运行详情（含执行轨迹）")
async def run_detail(
    run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    run = await db.get(AgentRun, run_id)
    if not run:
        raise NotFoundError("运行记录不存在")
    steps = (
        await db.execute(
            select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.step_index.asc())
        )
    ).scalars().all()
    return {
        "run": {
            "id": run.id,
            "application_id": run.application_id,
            "conversation_id": run.conversation_id,
            "status": run.status,
            "user_input": run.user_input,
            "output": run.output,
            "model_name": run.model_name,
            "mode": run.mode,
            "prompt_tokens": run.prompt_tokens,
            "completion_tokens": run.completion_tokens,
            "total_tokens": run.total_tokens,
            "steps_count": run.steps_count,
            "tool_calls": run.tool_calls,
            "duration_ms": run.duration_ms,
            "error": run.error,
            "created_at": run.created_at,
            "finished_at": run.finished_at,
        },
        "steps": [
            {
                "id": s.id,
                "step_index": s.step_index,
                "step_type": s.step_type,
                "content": s.content,
                "tool_name": s.tool_name,
                "tool_input": s.tool_input,
                "tool_output": s.tool_output,
                "duration_ms": s.duration_ms,
                "created_at": s.created_at,
            }
            for s in steps
        ],
    }
