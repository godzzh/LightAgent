"""工作流服务：执行、事件持久化。"""
from __future__ import annotations

import time
from typing import Any, AsyncIterator, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.exceptions import AppError, NotFoundError
from app.engines.nodes import NodeContext
from app.engines.workflow_engine import WorkflowEngine
from app.models.base import utcnow
from app.models.workflow import Workflow, WorkflowNodeRun, WorkflowRun
from app.providers.registry import build_provider_for_config, get_model_config
from app.services.knowledge.index import retrieve_segments


async def stream_workflow(
    *,
    workflow_id: str,
    inputs: dict[str, Any],
    application_id: Optional[str] = None,
    source: str = "debug",
    total_timeout: float = 300.0,
) -> AsyncIterator[dict[str, Any]]:
    started = time.perf_counter()
    async with SessionLocal() as db:
        wf = await db.get(Workflow, workflow_id)
        if not wf:
            raise NotFoundError("工作流不存在")

        engine = WorkflowEngine(wf.graph or {})

        run = WorkflowRun(
            workflow_id=wf.id,
            application_id=application_id,
            status="running",
            inputs=inputs,
            started_at=utcnow(),
            source=source,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        yield {"event": "run_started", "data": {"run_id": run.id, "workflow_id": wf.id}}
        yield {"event": "graph_loaded", "data": {"node_count": len((wf.graph or {}).get("nodes", []))}}

        async def get_provider(model_config_id: Optional[str]):
            cfg = await get_model_config(db, model_config_id)
            provider = await build_provider_for_config(db, cfg)
            return provider, cfg

        async def retrieve(dataset_ids: list[str], query: str, top_k: int, threshold: float):
            return await retrieve_segments(db, dataset_ids, query, top_k, threshold)

        ctx = NodeContext(db=db, get_provider=get_provider, retrieve=retrieve, run_inputs=inputs)

        async def emit(event: str, data: dict) -> None:
            # 由 stream() 统一转发，此处仅用于节点内部 token 事件，不做持久化
            pass

        ctx.emit = emit

        node_row_map: dict[str, WorkflowNodeRun] = {}
        error_msg = ""
        outputs: dict[str, Any] = {}
        usage: dict[str, Any] = {}
        try:
            async for ev in engine.stream(inputs, ctx, total_timeout=total_timeout):
                etype = ev["event"]
                data = ev["data"]

                if etype == "run_started":
                    # 引擎的 run_started 携带拓扑顺序，补充 run_id 后统一转发
                    yield {"event": "run_planned", "data": {**data, "run_id": run.id}}
                    continue

                if etype == "node_started":
                    row = WorkflowNodeRun(
                        run_id=run.id,
                        node_id=data["node_id"],
                        node_type=data.get("node_type", ""),
                        title=data.get("title", ""),
                        status="running",
                        order_index=len(node_row_map),
                    )
                    db.add(row)
                    await db.commit()
                    node_row_map[data["node_id"]] = row
                elif etype in ("node_completed", "node_failed"):
                    row = node_row_map.get(data.get("node_id", ""))
                    if row:
                        row.status = "succeeded" if etype == "node_completed" else "failed"
                        row.outputs = data.get("outputs") or {}
                        row.error = data.get("error") or ""
                        row.duration_ms = int(data.get("duration_ms") or 0)
                        row.logs = [{"event": etype, "at": utcnow().isoformat()}]
                        await db.commit()
                elif etype == "run_completed":
                    outputs = data.get("outputs") or {}
                    usage = data.get("usage") or {}
                    yield {"event": "run_completed", "data": {**data, "run_id": run.id}}
                    continue
                elif etype == "run_error":
                    error_msg = data.get("message", "执行失败")

                yield ev
        except Exception as exc:  # noqa: BLE001
            logger.exception("workflow run failed")
            error_msg = str(exc)
            yield {"event": "run_error", "data": {"message": error_msg}}

        duration_ms = int((time.perf_counter() - started) * 1000)
        run.status = "failed" if error_msg else "succeeded"
        run.outputs = outputs
        run.error = error_msg[:2000]
        run.finished_at = utcnow()
        run.duration_ms = duration_ms
        run.total_tokens = int((usage or {}).get("total_tokens") or 0)
        wf.run_count = (wf.run_count or 0) + 1
        await db.commit()

        if error_msg:
            yield {"event": "run_failed", "data": {"run_id": run.id, "message": error_msg}}


async def run_workflow(
    *, workflow_id: str, inputs: dict[str, Any], application_id: Optional[str] = None, source: str = "api"
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    async for ev in stream_workflow(
        workflow_id=workflow_id, inputs=inputs, application_id=application_id, source=source
    ):
        if ev["event"] == "run_completed":
            result = ev["data"]
        elif ev["event"] == "run_error":
            raise AppError(ev["data"].get("message", "工作流执行失败"))
    if not result:
        raise AppError("工作流未产生输出")
    return result
