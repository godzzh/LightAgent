"""工作流节点实现。

每个节点遵循统一接口：validate_config / validate_input / execute / validate_output。
节点通过 NodeContext 访问模型、知识库、工具与事件通道，保持与 API 层解耦。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationFailedError
from app.engines.safe_eval import safe_eval
from app.engines.variable_resolver import deep_render, render_template, resolve_path
from app.models.model_provider import ModelConfig
from app.providers.base import BaseLLMProvider, ChatMessage, Usage
from app.utils.net import validate_public_url

# 前端节点面板元数据
NODE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "start",
        "label": "开始",
        "description": "定义工作流输入参数",
        "icon": "play",
        "color": "#2563EB",
        "outputs": [],
    },
    {
        "type": "llm",
        "label": "大模型",
        "description": "调用大语言模型生成内容",
        "icon": "sparkles",
        "color": "#7C3AED",
        "outputs": [{"name": "text", "type": "string"}, {"name": "usage", "type": "object"}],
    },
    {
        "type": "knowledge",
        "label": "知识检索",
        "description": "从知识库检索相关片段",
        "icon": "book",
        "color": "#0EA5E9",
        "outputs": [{"name": "documents", "type": "array"}, {"name": "text", "type": "string"}],
    },
    {
        "type": "http",
        "label": "HTTP 请求",
        "description": "调用外部 HTTP 接口",
        "icon": "globe",
        "color": "#F59E0B",
        "outputs": [{"name": "status_code", "type": "number"}, {"name": "body", "type": "object"}],
    },
    {
        "type": "code",
        "label": "代码",
        "description": "受限表达式处理数据（安全沙箱）",
        "icon": "code",
        "color": "#334155",
        "outputs": [{"name": "result", "type": "any"}],
    },
    {
        "type": "condition",
        "label": "条件分支",
        "description": "按条件选择不同分支",
        "icon": "git-branch",
        "color": "#EC4899",
        "outputs": [{"name": "result", "type": "boolean"}],
        "branches": ["true", "false"],
    },
    {
        "type": "variable",
        "label": "变量赋值",
        "description": "设置或修改变量",
        "icon": "variable",
        "color": "#14B8A6",
        "outputs": [{"name": "value", "type": "any"}],
    },
    {
        "type": "answer",
        "label": "输出",
        "description": "定义最终输出内容",
        "icon": "message",
        "color": "#16A34A",
        "outputs": [],
    },
    {
        "type": "end",
        "label": "结束",
        "description": "结束工作流",
        "icon": "flag",
        "color": "#64748B",
        "outputs": [],
    },
]


class NodeExecutionError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class NodeContext:
    db: AsyncSession
    variables: dict[str, Any] = field(default_factory=dict)  # node_id -> outputs
    get_provider: Optional[Callable[[Optional[str]], Awaitable[tuple[BaseLLMProvider, ModelConfig]]]] = None
    retrieve: Optional[Callable[[list[str], str, int, float], Awaitable[list[dict]]]] = None
    emit: Optional[Callable[[str, dict], Awaitable[None]]] = None
    usage: Usage = field(default_factory=Usage)
    run_inputs: dict[str, Any] = field(default_factory=dict)
    answer: Optional[str] = None

    async def send(self, event: str, data: dict) -> None:
        if self.emit:
            await self.emit(event, data)

    def resolve(self, value: Any, *, strict: bool = False) -> Any:
        return deep_render(value, self.variables, strict=strict)


def _require(data: dict, key: str, label: str) -> Any:
    val = data.get(key)
    if val in (None, "", [], {}):
        raise ValidationFailedError(f"{label} 未配置")
    return val


# --------------------------------------------------------------------- start
async def run_start(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    params: list[dict] = data.get("params") or []
    outputs: dict[str, Any] = {}
    for p in params:
        name = p.get("name")
        if not name:
            continue
        if name in ctx.run_inputs:
            outputs[name] = ctx.run_inputs[name]
        elif p.get("required") and p.get("default") in (None, ""):
            raise NodeExecutionError(f"缺少必填输入参数: {name}")
        else:
            outputs[name] = p.get("default")
    # 透传未声明的输入（宽松模式，方便调试）
    for k, v in ctx.run_inputs.items():
        outputs.setdefault(k, v)
    return outputs


# ----------------------------------------------------------------------- llm
async def run_llm(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    if not ctx.get_provider:
        raise NodeExecutionError("模型服务不可用")
    provider, cfg = await ctx.get_provider(data.get("model_config_id"))
    system_prompt = ctx.resolve(data.get("system_prompt") or "")
    user_prompt = ctx.resolve(data.get("user_prompt") or "")
    if not user_prompt:
        raise ValidationFailedError("大模型节点缺少用户提示词")

    messages = []
    if system_prompt:
        messages.append(ChatMessage(role="system", content=render_template(system_prompt, ctx.variables)))
    messages.append(ChatMessage(role="user", content=render_template(user_prompt, ctx.variables)))

    text_parts: list[str] = []
    usage = Usage()
    async for ev in provider.chat_stream(
        cfg.model_name,
        messages,
        temperature=float(data.get("temperature", cfg.temperature)),
        top_p=float(data.get("top_p", cfg.top_p)),
        max_tokens=int(data.get("max_tokens", cfg.max_tokens)),
    ):
        if ev["type"] == "token":
            text_parts.append(ev["content"])
            await ctx.send("node_token", {"node_id": node["id"], "content": ev["content"]})
        elif ev["type"] == "usage":
            usage = Usage(**ev["usage"])
    ctx.usage.add(usage)
    text = "".join(text_parts)
    return {
        "text": text,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
    }


# ----------------------------------------------------------------- knowledge
async def run_knowledge(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    dataset_ids: list[str] = data.get("dataset_ids") or []
    if not dataset_ids:
        raise ValidationFailedError("知识检索节点未选择知识库")
    query = ctx.resolve(data.get("query") or "")
    if not query:
        raise ValidationFailedError("知识检索节点缺少检索问题")
    if not ctx.retrieve:
        raise NodeExecutionError("检索服务不可用")
    top_k = int(data.get("top_k", 4))
    threshold = float(data.get("threshold", 0.3))
    docs = await ctx.retrieve(dataset_ids, str(query), top_k, threshold)
    context_text = "\n\n".join(
        f"[{i + 1}] (来源: {d.get('document_name')}) {d.get('content')}" for i, d in enumerate(docs)
    )
    return {"documents": docs, "text": context_text}


# ---------------------------------------------------------------------- http
async def run_http(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    url = ctx.resolve(data.get("url") or "")
    if not url:
        raise ValidationFailedError("HTTP 节点缺少 URL")
    url = validate_public_url(str(url))
    method = str(data.get("method") or "GET").upper()
    headers = ctx.resolve(data.get("headers") or {})
    params = ctx.resolve(data.get("params") or {})
    body = ctx.resolve(data.get("body"))
    timeout = float(data.get("timeout") or 20)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            resp = await client.request(
                method,
                url,
                params=params or None,
                headers={k: str(v) for k, v in (headers or {}).items()},
                json=body if isinstance(body, (dict, list)) else None,
                content=body if isinstance(body, str) else None,
            )
    except httpx.TimeoutException as exc:
        raise NodeExecutionError(f"HTTP 请求超时({timeout}s)") from exc
    except httpx.HTTPError as exc:
        raise NodeExecutionError(f"HTTP 请求失败: {exc}") from exc

    try:
        parsed = resp.json()
    except Exception:  # noqa: BLE001
        parsed = None
    return {
        "status_code": resp.status_code,
        "body": parsed if parsed is not None else resp.text[:8000],
        "text": resp.text[:8000],
    }


# ---------------------------------------------------------------------- code
async def run_code(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    expression = data.get("expression") or ""
    if not expression:
        raise ValidationFailedError("代码节点缺少表达式")
    # 作用域：开始节点的输入参数以裸变量名暴露（query / n …），
    # 上游节点输出以节点 ID 暴露（llm_1.text / code_1.result）。
    scope: dict[str, Any] = dict(ctx.run_inputs or {})
    for k, v in ctx.variables.items():
        scope[k] = v
    result = safe_eval(expression, scope)
    outputs_key = data.get("output_key") or "result"
    return {outputs_key: result, "result": result}


# ----------------------------------------------------------------- condition
def _compare(left: Any, op: str, right: Any) -> bool:
    def num(v: Any) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ValidationFailedError(f"无法将 {v!r} 转换为数字比较") from None

    if op == "eq":
        return str(left) == str(right) if not isinstance(left, (int, float)) else left == right
    if op == "ne":
        return not _compare(left, "eq", right)
    if op == "gt":
        return num(left) > num(right)
    if op == "lt":
        return num(left) < num(right)
    if op == "gte":
        return num(left) >= num(right)
    if op == "lte":
        return num(left) <= num(right)
    if op == "contains":
        return str(right) in str(left)
    if op == "not_contains":
        return str(right) not in str(left)
    if op == "empty":
        return left in (None, "", [], {})
    if op == "not_empty":
        return left not in (None, "", [], {})
    if op == "in":
        return str(left) in str(right)
    raise ValidationFailedError(f"不支持的条件运算符: {op}")


async def run_condition(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    left = ctx.resolve(data.get("left"))
    right = ctx.resolve(data.get("right"))
    op = data.get("operator") or "eq"
    result = _compare(left, op, right)
    return {"result": result, "branch": "true" if result else "false"}


# ------------------------------------------------------------------ variable
async def run_variable(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    name = data.get("name")
    if not name:
        raise ValidationFailedError("变量赋值节点缺少变量名")
    value = ctx.resolve(data.get("value"))
    ctx.variables.setdefault("__vars__", {})[name] = value
    return {"name": name, "value": value}


# -------------------------------------------------------------------- answer
async def run_answer(node: dict, ctx: NodeContext) -> dict:
    data = node.get("data") or {}
    template = data.get("answer") or ""
    text = render_template(str(template), ctx.variables, strict=False, keep_unknown=False)
    if not text and data.get("value"):
        text = str(ctx.resolve(data.get("value")))
    ctx.answer = text
    return {"answer": text}


async def run_end(node: dict, ctx: NodeContext) -> dict:
    return {"output": ctx.answer or ""}


NODE_EXECUTORS: dict[str, Callable[[dict, NodeContext], Awaitable[dict]]] = {
    "start": run_start,
    "llm": run_llm,
    "knowledge": run_knowledge,
    "http": run_http,
    "code": run_code,
    "condition": run_condition,
    "variable": run_variable,
    "answer": run_answer,
    "end": run_end,
}
