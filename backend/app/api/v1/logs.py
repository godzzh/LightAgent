"""运行日志与统计接口。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import Pagination, get_current_user, paginate
from app.core.response import EnvelopeRoute
from app.models.application import Application
from app.models.run import LlmCallLog
from app.models.user import User
from app.models.workflow import Workflow, WorkflowRun
from app.services.workspace_service import get_user_workspace

router = APIRouter(route_class=EnvelopeRoute, prefix="/logs", tags=["运行日志"])


def _kw_variants(keyword: str) -> list[str]:
    """历史数据中中文可能以 \\uXXXX 形式存进 JSON 字段，补充转义形态一起匹配。"""
    escaped = json.dumps(keyword, ensure_ascii=True)[1:-1]
    return [keyword] if escaped == keyword else [keyword, escaped]


@router.get("/runs", summary="统一运行日志（Agent + Workflow）")
async def list_runs(
    run_type: str = Query("agent", pattern="^(agent|workflow|llm)$"),
    status: Optional[str] = None,
    keyword: str = "",
    app_id: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_user_workspace(db, user)
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

    if run_type == "agent":
        from app.models.run import AgentRun

        # 注意：select(Application.id) 的 scalars 已返回主键值本身，不能再取 .id
        app_ids: list[str] = list(
            (await db.execute(select(Application.id).where(Application.workspace_id == ws.id))).scalars().all()
        )
        if not app_ids:
            return paginate([], 0, p)
        base = select(AgentRun).where(AgentRun.application_id.in_(app_ids), AgentRun.created_at >= since)
        cnt = select(func.count(AgentRun.id)).where(
            AgentRun.application_id.in_(app_ids), AgentRun.created_at >= since
        )
        if app_id:
            base = base.where(AgentRun.application_id == app_id)
            cnt = cnt.where(AgentRun.application_id == app_id)
        if status:
            base = base.where(AgentRun.status == status)
            cnt = cnt.where(AgentRun.status == status)
        if keyword:
            cond = or_(AgentRun.user_input.contains(keyword), AgentRun.output.contains(keyword))
            base = base.where(cond)
            cnt = cnt.where(cond)
        total = (await db.execute(cnt)).scalar_one()
        rows = (
            await db.execute(base.order_by(AgentRun.created_at.desc()).offset(p.offset).limit(p.page_size))
        ).scalars().all()
        name_map = {
            a.id: a.name
            for a in (await db.execute(select(Application).where(Application.id.in_(app_ids)))).scalars().all()
        }
        return paginate(
            [
                {
                    "id": r.id,
                    "type": "agent",
                    "app_id": r.application_id,
                    "app_name": name_map.get(r.application_id, ""),
                    "user_input": (r.user_input or "")[:200],
                    "output": (r.output or "")[:200],
                    "status": r.status,
                    "model_name": r.model_name,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "total_tokens": r.total_tokens,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                    "created_at": r.created_at,
                }
                for r in rows
            ],
            int(total),
            p,
        )

    if run_type == "workflow":
        wf_ids: list[str] = list(
            (await db.execute(select(Workflow.id).where(Workflow.workspace_id == ws.id))).scalars().all()
        )
        if not wf_ids:
            return paginate([], 0, p)
        base = select(WorkflowRun).where(
            WorkflowRun.workflow_id.in_(wf_ids), WorkflowRun.created_at >= since
        )
        cnt = select(func.count(WorkflowRun.id)).where(
            WorkflowRun.workflow_id.in_(wf_ids), WorkflowRun.created_at >= since
        )
        if app_id:
            base = base.where(WorkflowRun.workflow_id == app_id)
            cnt = cnt.where(WorkflowRun.workflow_id == app_id)
        if status:
            base = base.where(WorkflowRun.status == status)
            cnt = cnt.where(WorkflowRun.status == status)
        if keyword:
            cond = or_(
                *[
                    cast(col, Text).contains(v)
                    for v in _kw_variants(keyword)
                    for col in (WorkflowRun.inputs, WorkflowRun.outputs)
                ]
            )
            base = base.where(cond)
            cnt = cnt.where(cond)
        total = (await db.execute(cnt)).scalar_one()
        rows = (
            await db.execute(base.order_by(WorkflowRun.created_at.desc()).offset(p.offset).limit(p.page_size))
        ).scalars().all()
        wf_map = {
            w.id: w.name
            for w in (
                await db.execute(select(Workflow).where(Workflow.id.in_(wf_ids)))
            ).scalars().all()
        }
        return paginate(
            [
                {
                    "id": r.id,
                    "type": "workflow",
                    "app_id": r.workflow_id,
                    "app_name": wf_map.get(r.workflow_id, ""),
                    "user_input": str(r.inputs)[:200],
                    "output": str(r.outputs)[:200],
                    "status": r.status,
                    "model_name": "",
                    "total_tokens": r.total_tokens,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                    "created_at": r.created_at,
                }
                for r in rows
            ],
            int(total),
            p,
        )

    # llm 调用日志
    base = select(LlmCallLog).where(LlmCallLog.created_at >= since)
    cnt = select(func.count(LlmCallLog.id)).where(LlmCallLog.created_at >= since)
    if status:
        base = base.where(LlmCallLog.status == status)
        cnt = cnt.where(LlmCallLog.status == status)
    if keyword:
        base = base.where(LlmCallLog.model_name.contains(keyword))
        cnt = cnt.where(LlmCallLog.model_name.contains(keyword))
    total = (await db.execute(cnt)).scalar_one()
    rows = (
        await db.execute(base.order_by(LlmCallLog.created_at.desc()).offset(p.offset).limit(p.page_size))
    ).scalars().all()
    return paginate(
        [
            {
                "id": r.id,
                "type": "llm",
                "app_id": r.application_id,
                "app_name": "",
                "user_input": "",
                "output": "",
                "status": r.status,
                "model_name": r.model_name,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "duration_ms": r.latency_ms,
                "error": r.error,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        int(total),
        p,
    )


@router.get("/stats", summary="Token 与调用统计")
async def stats(
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                func.count(LlmCallLog.id),
                func.coalesce(func.sum(LlmCallLog.prompt_tokens), 0),
                func.coalesce(func.sum(LlmCallLog.completion_tokens), 0),
                func.coalesce(func.sum(LlmCallLog.latency_ms), 0),
            ).where(LlmCallLog.created_at >= since)
        )
    ).one()
    failed = (
        await db.execute(
            select(func.count(LlmCallLog.id)).where(
                LlmCallLog.created_at >= since, LlmCallLog.status == "failed"
            )
        )
    ).scalar_one()
    calls = int(rows[0] or 0)
    return {
        "days": days,
        "calls": calls,
        "failed": int(failed),
        "prompt_tokens": int(rows[1] or 0),
        "completion_tokens": int(rows[2] or 0),
        "avg_latency_ms": int((rows[3] or 0) / calls) if calls else 0,
    }
