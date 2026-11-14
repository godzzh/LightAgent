"""工作流接口：图管理、校验、运行（SSE）、运行记录。"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import Pagination, get_current_user, paginate
from app.core.exceptions import AppError, NotFoundError
from app.core.response import EnvelopeRoute
from app.engines.nodes import NODE_DEFINITIONS
from app.engines.workflow_engine import WorkflowEngine
from app.models.user import User
from app.models.workflow import Workflow, WorkflowNodeRun, WorkflowRun, WorkflowVersion
from app.schemas.knowledge import WorkflowCreate, WorkflowRunRequest, WorkflowUpdate
from app.services.workflow.service import run_workflow, stream_workflow
from app.utils.sse import sse_response

router = APIRouter(route_class=EnvelopeRoute, prefix="/workflows", tags=["工作流"])


def default_graph() -> dict[str, Any]:
    start_id = "start_1"
    end_id = "end_1"
    return {
        "nodes": [
            {
                "id": start_id,
                "type": "start",
                "position": {"x": 80, "y": 200},
                "data": {
                    "title": "开始",
                    "params": [
                        {"name": "query", "type": "string", "required": True, "default": "", "description": "用户问题"}
                    ],
                },
            },
            {
                "id": end_id,
                "type": "end",
                "position": {"x": 640, "y": 200},
                "data": {"title": "结束"},
            },
        ],
        "edges": [{"id": "e_start_end", "source": start_id, "target": end_id}],
    }


def _wf_out(w: Workflow) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "graph": w.graph or {},
        "version": w.version,
        "status": w.status,
        "run_count": w.run_count,
        "created_at": w.created_at,
        "updated_at": w.updated_at,
    }


@router.get("/node-definitions", summary="可用节点类型")
async def node_definitions(user: User = Depends(get_current_user)):
    return NODE_DEFINITIONS


@router.get("", summary="工作流列表")
async def list_workflows(
    keyword: str = "",
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Workflow)
    count_stmt = select(func.count(Workflow.id))
    if keyword:
        stmt = stmt.where(Workflow.name.contains(keyword))
        count_stmt = count_stmt.where(Workflow.name.contains(keyword))
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(Workflow.updated_at.desc()).offset(p.offset).limit(p.page_size))
    ).scalars().all()
    return paginate(
        [
            {**_wf_out(w), "graph": {"node_count": len((w.graph or {}).get("nodes", []))}}
            for w in rows
        ],
        int(total),
        p,
    )


@router.post("", summary="创建工作流")
async def create_workflow(
    payload: WorkflowCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.workspace_service import get_user_workspace

    ws = await get_user_workspace(db, user)
    wf = Workflow(
        workspace_id=ws.id,
        name=payload.name,
        description=payload.description,
        graph=payload.graph or default_graph(),
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return _wf_out(wf)


@router.get("/{workflow_id}", summary="工作流详情")
async def get_workflow(
    workflow_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise NotFoundError("工作流不存在")
    return _wf_out(wf)


@router.patch("/{workflow_id}", summary="保存工作流（自动生成版本快照）")
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise NotFoundError("工作流不存在")
    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.graph is not None:
        wf.graph = payload.graph
        wf.version = (wf.version or 1) + 1
        db.add(
            WorkflowVersion(
                workflow_id=wf.id, version=wf.version, graph=payload.graph, note="手动保存"
            )
        )
    await db.commit()
    await db.refresh(wf)
    return _wf_out(wf)


@router.delete("/{workflow_id}", summary="删除工作流")
async def delete_workflow(
    workflow_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise NotFoundError("工作流不存在")
    await db.delete(wf)
    await db.commit()
    return {"ok": True}


@router.post("/{workflow_id}/validate", summary="校验工作流图")
async def validate_workflow(
    workflow_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise NotFoundError("工作流不存在")
    check = WorkflowEngine(wf.graph or {}).validate()
    return {"ok": check.ok, "errors": check.errors}


@router.post("/{workflow_id}/run", summary="运行工作流（stream=true 返回 SSE）")
async def run(
    workflow_id: str,
    payload: WorkflowRunRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise NotFoundError("工作流不存在")

    if payload.stream:
        return sse_response(
            stream_workflow(workflow_id=workflow_id, inputs=payload.inputs, source="debug")
        )
    return await run_workflow(workflow_id=workflow_id, inputs=payload.inputs, source="debug")


@router.get("/{workflow_id}/runs", summary="运行记录")
async def list_runs(
    workflow_id: str,
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = (
        await db.execute(select(func.count(WorkflowRun.id)).where(WorkflowRun.workflow_id == workflow_id))
    ).scalar_one()
    rows = (
        await db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(WorkflowRun.created_at.desc())
            .offset(p.offset)
            .limit(p.page_size)
        )
    ).scalars().all()
    return paginate(
        [
            {
                "id": r.id,
                "status": r.status,
                "inputs": r.inputs,
                "outputs": r.outputs,
                "error": r.error,
                "duration_ms": r.duration_ms,
                "total_tokens": r.total_tokens,
                "source": r.source,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        int(total),
        p,
    )


@router.get("/runs/{run_id}", summary="运行详情（节点轨迹）")
async def run_detail(
    run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    run_row = await db.get(WorkflowRun, run_id)
    if not run_row:
        raise NotFoundError("运行记录不存在")
    nodes = (
        await db.execute(
            select(WorkflowNodeRun)
            .where(WorkflowNodeRun.run_id == run_id)
            .order_by(WorkflowNodeRun.order_index.asc())
        )
    ).scalars().all()
    return {
        "run": {
            "id": run_row.id,
            "workflow_id": run_row.workflow_id,
            "status": run_row.status,
            "inputs": run_row.inputs,
            "outputs": run_row.outputs,
            "error": run_row.error,
            "duration_ms": run_row.duration_ms,
            "total_tokens": run_row.total_tokens,
            "created_at": run_row.created_at,
        },
        "nodes": [
            {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "title": n.title,
                "status": n.status,
                "inputs": n.inputs,
                "outputs": n.outputs,
                "error": n.error,
                "duration_ms": n.duration_ms,
            }
            for n in nodes
        ],
    }
