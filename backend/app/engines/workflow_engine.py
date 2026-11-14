"""轻量级 DAG 工作流执行引擎。

职责：图校验 → 拓扑排序 → 按依赖执行 → 条件分支 → 节点事件推送 → 结果汇总。
执行过程完全在后端进行，前端只负责展示事件。
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from loguru import logger

from app.core.exceptions import ValidationFailedError
from app.engines.nodes import NODE_EXECUTORS, NodeContext, NodeExecutionError


@dataclass
class GraphCheck:
    ok: bool = True
    errors: list[str] = field(default_factory=list)


class WorkflowEngine:
    MAX_NODES = 200

    def __init__(self, graph: dict[str, Any]):
        self.graph = graph or {}
        self.nodes: list[dict[str, Any]] = list(self.graph.get("nodes") or [])
        self.edges: list[dict[str, Any]] = list(self.graph.get("edges") or [])
        self._node_map = {n["id"]: n for n in self.nodes if "id" in n}

    # ------------------------------------------------------------ validation
    def validate(self) -> GraphCheck:
        check = GraphCheck()
        if not self.nodes:
            check.ok = False
            check.errors.append("工作流为空，请至少添加开始与结束节点")
            return check
        if len(self.nodes) > self.MAX_NODES:
            check.ok = False
            check.errors.append(f"节点数量超过上限({self.MAX_NODES})")

        types = [n.get("type") for n in self.nodes]
        if "start" not in types:
            check.errors.append("缺少开始(Start)节点")
        if not any(t in ("answer", "end") for t in types):
            check.errors.append("缺少输出(Answer)或结束(End)节点")

        ids = [n.get("id") for n in self.nodes]
        if len(ids) != len(set(ids)):
            check.errors.append("存在重复的节点 ID")

        for e in self.edges:
            if e.get("source") not in self._node_map:
                check.errors.append(f"连线 {e.get('id')} 的起点节点不存在")
            if e.get("target") not in self._node_map:
                check.errors.append(f"连线 {e.get('id')} 的终点节点不存在")
            if e.get("source") == e.get("target"):
                check.errors.append("存在自连线的节点")

        if self._has_cycle():
            check.errors.append("工作流存在环，无法按 DAG 执行")

        for n in self.nodes:
            if n.get("type") not in NODE_EXECUTORS:
                check.errors.append(f"未知节点类型: {n.get('type')}")
        check.ok = not check.errors
        return check

    def _has_cycle(self) -> bool:
        indeg: dict[str, int] = {nid: 0 for nid in self._node_map}
        adj: dict[str, list[str]] = defaultdict(list)
        for e in self.edges:
            s, t = e.get("source"), e.get("target")
            if s in indeg and t in indeg:
                adj[s].append(t)
                indeg[t] += 1
        queue = [n for n, d in indeg.items() if d == 0]
        seen = 0
        while queue:
            cur = queue.pop()
            seen += 1
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        return seen != len(indeg)

    def topo_order(self) -> list[str]:
        indeg: dict[str, int] = {nid: 0 for nid in self._node_map}
        adj: dict[str, list[str]] = defaultdict(list)
        for e in self.edges:
            s, t = e.get("source"), e.get("target")
            if s in indeg and t in indeg:
                adj[s].append(t)
                indeg[t] += 1
        queue = [nid for nid, d in indeg.items() if d == 0]
        # start 优先
        queue.sort(key=lambda nid: 0 if self._node_map[nid].get("type") == "start" else 1)
        order: list[str] = []
        while queue:
            cur = queue.pop(0)
            order.append(cur)
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        return order

    # ---------------------------------------------------------------- execute
    async def stream(
        self,
        inputs: dict[str, Any],
        ctx: NodeContext,
        *,
        total_timeout: float = 300.0,
    ) -> AsyncIterator[dict[str, Any]]:
        check = self.validate()
        if not check.ok:
            yield {"event": "run_error", "data": {"message": "；".join(check.errors), "type": "graph_invalid"}}
            return

        order = self.topo_order()
        incoming: dict[str, list[dict]] = defaultdict(list)
        for e in self.edges:
            incoming[e["target"]].append(e)

        executed: dict[str, dict[str, Any]] = {}
        active_nodes: set[str] = set()
        started = time.perf_counter()
        nodes_run = 0

        yield {
            "event": "run_started",
            "data": {"order": order, "inputs": inputs, "total_nodes": len(order)},
        }

        try:
            import asyncio

            async with asyncio.timeout(total_timeout):
                for node_id in order:
                    node = self._node_map[node_id]
                    ntype = node.get("type", "")
                    title = (node.get("data") or {}).get("title") or ntype
                    node_in = incoming.get(node_id, [])

                    # 分支判断：条件节点按 sourceHandle 选择路径
                    should_run = True
                    if ntype != "start" and node_in:
                        should_run = False
                        for e in node_in:
                            src = e.get("source")
                            if src not in executed:
                                continue
                            src_out = executed[src]
                            handle = e.get("sourceHandle")
                            if handle and src_out.get("branch") and handle != src_out["branch"]:
                                continue
                            should_run = True
                            break
                    elif ntype != "start" and not node_in:
                        should_run = False

                    if not should_run:
                        yield {"event": "node_skipped", "data": {"node_id": node_id, "title": title}}
                        continue

                    nodes_run += 1
                    if nodes_run > self.MAX_NODES:
                        raise ValidationFailedError("节点执行数量超过上限")

                    yield {
                        "event": "node_started",
                        "data": {"node_id": node_id, "node_type": ntype, "title": title},
                    }
                    t0 = time.perf_counter()
                    try:
                        executor = NODE_EXECUTORS[ntype]
                        outputs = await executor(node, ctx)
                        executed[node_id] = outputs
                        ctx.variables[node_id] = outputs
                        active_nodes.add(node_id)
                        yield {
                            "event": "node_completed",
                            "data": {
                                "node_id": node_id,
                                "node_type": ntype,
                                "title": title,
                                "outputs": outputs,
                                "duration_ms": int((time.perf_counter() - t0) * 1000),
                            },
                        }
                    except (ValidationFailedError, NodeExecutionError) as exc:
                        msg = getattr(exc, "message", str(exc))
                        yield {
                            "event": "node_failed",
                            "data": {"node_id": node_id, "title": title, "error": msg},
                        }
                        yield {"event": "run_error", "data": {"message": f"节点「{title}」执行失败: {msg}"}}
                        return
                    except Exception as exc:  # noqa: BLE001
                        logger.exception(f"workflow node {node_id} error")
                        yield {
                            "event": "node_failed",
                            "data": {"node_id": node_id, "title": title, "error": str(exc)},
                        }
                        yield {"event": "run_error", "data": {"message": f"节点「{title}」异常: {exc}"}}
                        return

                yield {
                    "event": "run_completed",
                    "data": {
                        "outputs": {"answer": ctx.answer or ""},
                        "node_outputs": executed,
                        "usage": ctx.usage.__dict__,
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                        "executed_nodes": list(active_nodes),
                    },
                }
        except TimeoutError:
            yield {"event": "run_error", "data": {"message": f"工作流执行超时({total_timeout}s)"}}
        except asyncio.CancelledError:
            logger.info("workflow run cancelled")
            raise
