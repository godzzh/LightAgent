"""工作空间 Dashboard 统计接口。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import EnvelopeRoute
from app.models.application import Application
from app.models.knowledge import Dataset
from app.models.run import AgentRun
from app.models.user import User
from app.models.workflow import Workflow, WorkflowRun
from app.services.workspace_service import get_user_workspace

router = APIRouter(route_class=EnvelopeRoute, prefix="/dashboard", tags=["工作空间"])


@router.get("/overview", summary="概览统计")
async def overview(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await get_user_workspace(db, user)

    app_total = (
        await db.execute(select(func.count(Application.id)).where(Application.workspace_id == ws.id))
    ).scalar_one()
    published = (
        await db.execute(
            select(func.count(Application.id)).where(
                Application.workspace_id == ws.id, Application.status == "published"
            )
        )
    ).scalar_one()
    dataset_total = (
        await db.execute(select(func.count(Dataset.id)).where(Dataset.workspace_id == ws.id))
    ).scalar_one()
    workflow_total = (
        await db.execute(select(func.count(Workflow.id)).where(Workflow.workspace_id == ws.id))
    ).scalar_one()

    # 注意：select(Application.id) 的 scalars 返回的是主键值本身，不能再取 .id
    app_ids: list[str] = list(
        (
            await db.execute(select(Application.id).where(Application.workspace_id == ws.id))
        ).scalars().all()
    )

    run_total = 0
    tokens = 0
    if app_ids:
        run_total = (
            await db.execute(
                select(func.count(AgentRun.id)).where(AgentRun.application_id.in_(app_ids))
            )
        ).scalar_one()
        tokens = (
            await db.execute(
                select(func.coalesce(func.sum(AgentRun.total_tokens), 0)).where(
                    AgentRun.application_id.in_(app_ids)
                )
            )
        ).scalar_one()

    wf_ids: list[str] = list(
        (await db.execute(select(Workflow.id).where(Workflow.workspace_id == ws.id))).scalars().all()
    )
    wf_runs = 0
    if wf_ids:
        wf_runs = (
            await db.execute(select(func.count(WorkflowRun.id)).where(WorkflowRun.workflow_id.in_(wf_ids)))
        ).scalar_one()

    return {
        "workspace": {"id": ws.id, "name": ws.name, "description": ws.description},
        "stats": {
            "applications": int(app_total),
            "published": int(published),
            "datasets": int(dataset_total),
            "workflows": int(workflow_total),
            "runs": int(run_total or 0) + int(wf_runs or 0),
            "tokens": int(tokens or 0),
        },
    }


@router.get("/recent", summary="最近应用与运行记录")
async def recent(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await get_user_workspace(db, user)
    apps = (
        await db.execute(
            select(Application)
            .where(Application.workspace_id == ws.id)
            .order_by(Application.created_at.desc())
            .limit(5)
        )
    ).scalars().all()

    app_ids: list[str] = list(
        (await db.execute(select(Application.id).where(Application.workspace_id == ws.id))).scalars().all()
    )
    runs = []
    if app_ids:
        rows = (
            await db.execute(
                select(AgentRun)
                .where(AgentRun.application_id.in_(app_ids))
                .order_by(AgentRun.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
        name_map = {a.id: a.name for a in (await db.execute(select(Application).where(Application.id.in_(app_ids)))).scalars().all()}
        runs = [
            {
                "id": r.id,
                "application_id": r.application_id,
                "application_name": name_map.get(r.application_id, "已删除应用"),
                "status": r.status,
                "user_input": (r.user_input or "")[:60],
                "total_tokens": r.total_tokens,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    return {
        "applications": [
            {
                "id": a.id,
                "name": a.name,
                "app_type": a.app_type,
                "status": a.status,
                "icon": a.icon,
                "created_at": a.created_at,
            }
            for a in apps
        ],
        "runs": runs,
    }


@router.get("/trend", summary="调用趋势（近 7 天）与模型使用分布")
async def trend(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await get_user_workspace(db, user)
    app_ids: list[str] = list(
        (await db.execute(select(Application.id).where(Application.workspace_id == ws.id))).scalars().all()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=6)
    days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    buckets = {d: 0 for d in days}

    models: dict[str, int] = {}
    if app_ids:
        rows = (
            await db.execute(
                select(AgentRun.created_at, AgentRun.model_name).where(
                    AgentRun.application_id.in_(app_ids), AgentRun.created_at >= since
                )
            )
        ).all()
        for created, model_name in rows:
            key = created.strftime("%Y-%m-%d")
            if key in buckets:
                buckets[key] += 1
            if model_name:
                models[model_name] = models.get(model_name, 0) + 1

    return {
        "trend": [{"date": d, "count": buckets[d]} for d in days],
        "models": [{"name": k, "count": v} for k, v in sorted(models.items(), key=lambda x: -x[1])],
    }
