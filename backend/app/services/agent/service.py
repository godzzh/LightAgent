"""Agent 应用服务：装配运行时、执行对话、持久化会话与运行记录。

SSE 输出事件与 AgentRuntime 内部事件一一对应，额外补充 run_started / run_completed 的元信息。
"""
from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.exceptions import AppError, NotFoundError
from app.engines.agent_runtime import AgentRuntime, AgentRuntimeConfig
from app.models.application import Application, Conversation, Message
from app.models.base import utcnow
from app.models.run import AgentRun, AgentStep, LlmCallLog
from app.providers.registry import build_provider_for_config, get_model_config
from app.services.knowledge.index import retrieve_segments
from app.services.tools.tool_service import resolve_tools


async def load_application(db: AsyncSession, application_id: str) -> Application:
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("应用不存在")
    return app


async def build_runtime(db: AsyncSession, app: Application) -> AgentRuntime:
    cfg = app.config or {}
    model_config = await get_model_config(db, app.model_config_id or cfg.get("model_config_id"))
    provider = await build_provider_for_config(db, model_config)

    tool_keys = None
    if cfg.get("enable_tools", True):
        tool_keys = [t.get("tool_key") for t in cfg.get("tools") or [] if t.get("enabled", True)]
        if not tool_keys:
            tool_keys = []  # 显式空列表表示未选择工具

    tools = await resolve_tools(db, tool_keys, workspace_id=app.workspace_id) if tool_keys is not None else []

    dataset_ids = [d for d in (cfg.get("dataset_ids") or []) if d]
    retriever = None
    if cfg.get("enable_knowledge", True) and dataset_ids:
        async def retriever_fn(query: str, top_k: int, threshold: float):
            return await retrieve_segments(db, dataset_ids, query, top_k, threshold)

        retriever = retriever_fn

    runtime_cfg = AgentRuntimeConfig(
        system_prompt=cfg.get("system_prompt") or "你是一个乐于助人的 AI 助手。",
        user_prompt_template=cfg.get("user_prompt") or "{{query}}",
        mode=cfg.get("mode") or "function_calling",
        max_steps=int(cfg.get("max_steps", 8)),
        max_tool_calls=int(cfg.get("max_tool_calls", 6)),
        max_context_messages=int(cfg.get("max_context_messages", 20)),
        total_timeout=float(cfg.get("total_timeout", 180)),
        tool_timeout=float(cfg.get("tool_timeout", 25)),
        temperature=float(cfg.get("temperature", model_config.temperature)),
        top_p=float(cfg.get("top_p", model_config.top_p)),
        max_tokens=int(cfg.get("max_tokens", model_config.max_tokens)),
        enable_tools=bool(cfg.get("enable_tools", True)) and bool(tools),
        enable_memory=bool(cfg.get("enable_memory", True)),
        knowledge_top_k=int(cfg.get("knowledge_top_k", 4)),
        knowledge_threshold=float(cfg.get("knowledge_threshold", 0.3)),
    )
    return AgentRuntime(
        provider=provider,
        model_name=model_config.model_name,
        config=runtime_cfg,
        tools=tools,
        knowledge_retriever=retriever,
        supports_tool_call=bool(model_config.supports_tool_call),
    )


async def _get_or_create_conversation(
    db: AsyncSession, app_id: str, session_id: str, *, user_id: Optional[str], source: str
) -> Conversation:
    conv = (
        await db.execute(
            select(Conversation).where(
                Conversation.application_id == app_id, Conversation.session_id == session_id
            )
        )
    ).scalar_one_or_none()
    if conv:
        return conv
    conv = Conversation(application_id=app_id, session_id=session_id, user_id=user_id, source=source)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def load_history(db: AsyncSession, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in reversed(rows) if m.role in ("user", "assistant")]
    return history


async def stream_chat(
    *,
    application_id: str,
    query: str,
    session_id: str,
    source: str = "debug",
    user_id: Optional[str] = None,
    regenerate_history: Optional[list[dict[str, Any]]] = None,
) -> AsyncIterator[dict[str, Any]]:
    """执行一次 Agent 对话，产出 SSE 事件。内部自管 Session，适配 StreamingResponse。"""
    started = time.perf_counter()
    async with SessionLocal() as db:
        app = await load_application(db, application_id)
        if app.app_type == "workflow":
            raise AppError("工作流应用请使用工作流运行接口")

        conv = await _get_or_create_conversation(db, app.id, session_id, user_id=user_id, source=source)
        history = await load_history(db, conv.id)

        runtime = await build_runtime(db, app)
        run = AgentRun(
            application_id=app.id,
            conversation_id=conv.id,
            status="running",
            user_input=query,
            mode=runtime.cfg.mode,
            model_name=runtime.model_name,
            started_at=utcnow(),
            source=source,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        user_msg = Message(conversation_id=conv.id, role="user", content=query)
        db.add(user_msg)
        if conv.title in ("新会话", "") and query:
            conv.title = query[:30]
        await db.commit()

        yield {"event": "run_started", "data": {"run_id": run.id, "session_id": session_id, "app_id": app.id}}

        output_parts: list[str] = []
        steps: list[dict[str, Any]] = []
        step_index = 0
        error_msg = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            async for ev in runtime.stream(query, history):
                etype = ev["event"]
                data = ev["data"]
                if etype == "run_started":
                    continue  # 服务层已发出带 run_id 的 run_started
                if etype == "token":
                    output_parts.append(data.get("content", ""))
                elif etype == "run_completed":
                    usage = data.get("usage") or usage
                    yield {"event": "run_completed", "data": {**data, "run_id": run.id}}
                    continue
                elif etype == "run_error":
                    error_msg = data.get("message", "执行失败")
                if etype in ("tool_call", "tool_result", "step", "knowledge"):
                    steps.append({"event": etype, "data": data})

                # 不向前端透传完整 prompt（可能含敏感信息），仅保留必要上下文
                if etype == "context":
                    safe = {"messages": [{"role": m["role"], "content_len": len(m.get("content") or "")} for m in data.get("messages", [])]}
                    yield {"event": "context", "data": safe}
                    continue
                yield ev

                if etype == "tool_call":
                    db.add(
                        AgentStep(
                            run_id=run.id,
                            step_index=step_index,
                            step_type="action",
                            content=json.dumps(data.get("arguments"), ensure_ascii=False),
                            tool_name=data.get("name"),
                            tool_input=data.get("arguments") or {},
                        )
                    )
                    step_index += 1
                elif etype == "tool_result":
                    db.add(
                        AgentStep(
                            run_id=run.id,
                            step_index=step_index,
                            step_type="observation",
                            content=str(data.get("output"))[:4000],
                            tool_name=data.get("name"),
                            tool_output=data.get("output"),
                            duration_ms=int(data.get("duration_ms") or 0),
                        )
                    )
                    step_index += 1
                    await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("agent stream failed")
            error_msg = str(exc)
            yield {"event": "run_error", "data": {"message": error_msg}}

        duration_ms = int((time.perf_counter() - started) * 1000)
        output = "".join(output_parts)

        # ---- 落库 ----
        run.status = "failed" if error_msg else "succeeded"
        run.output = output
        run.error = error_msg[:2000]
        run.finished_at = utcnow()
        run.duration_ms = duration_ms
        run.steps_count = runtime.state.steps
        run.tool_calls = runtime.state.tool_calls
        run.prompt_tokens = usage.get("prompt_tokens", 0)
        run.completion_tokens = usage.get("completion_tokens", 0)
        run.total_tokens = usage.get("total_tokens", 0)
        run.extra = {"knowledge_chunks": steps and [s for s in steps if s["event"] == "knowledge"][:1]}

        if output:
            db.add(
                Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=output,
                    prompt_tokens=run.prompt_tokens,
                    completion_tokens=run.completion_tokens,
                )
            )
        db.add(
            LlmCallLog(
                run_id=run.id,
                application_id=app.id,
                provider="",
                model_name=runtime.model_name,
                prompt_tokens=run.prompt_tokens,
                completion_tokens=run.completion_tokens,
                total_tokens=run.total_tokens,
                latency_ms=duration_ms,
                status="failed" if error_msg else "success",
                error=error_msg[:1000],
            )
        )
        app.run_count = (app.run_count or 0) + 1
        await db.commit()

        if error_msg:
            yield {"event": "run_failed", "data": {"run_id": run.id, "message": error_msg}}


async def chat_once(
    *, application_id: str, query: str, session_id: str, source: str = "api", user_id: Optional[str] = None
) -> dict[str, Any]:
    """非流式调用，返回最终结果。"""
    final: dict[str, Any] = {}
    async for ev in stream_chat(
        application_id=application_id, query=query, session_id=session_id, source=source, user_id=user_id
    ):
        if ev["event"] == "run_completed":
            final = ev["data"]
        elif ev["event"] == "run_error":
            raise AppError(ev["data"].get("message", "执行失败"))
    if not final:
        raise AppError("未能获取模型输出")
    return final
