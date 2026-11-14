"""工作流引擎测试：DAG 校验、变量解析、条件分支、节点失败。"""
from __future__ import annotations

import pytest

from app.engines.nodes import NodeContext
from app.engines.variable_resolver import render_template, resolve_path
from app.engines.workflow_engine import WorkflowEngine
from app.core.exceptions import ValidationFailedError


def graph(nodes, edges):
    return {"nodes": nodes, "edges": edges}


def node(nid, ntype, data=None):
    return {"id": nid, "type": ntype, "data": data or {}, "position": {"x": 0, "y": 0}}


BRANCH_GRAPH = graph(
    [
        node("start_1", "start", {"params": [{"name": "score", "type": "number", "required": True}]}),
        node("cond_1", "condition", {"left": "{{start_1.score}}", "operator": "gt", "right": "60"}),
        node("answer_yes", "answer", {"answer": "及格：{{start_1.score}}"}),
        node("answer_no", "answer", {"answer": "不及格"}),
        node("end_1", "end", {}),
    ],
    [
        {"id": "e1", "source": "start_1", "target": "cond_1"},
        {"id": "e2", "source": "cond_1", "target": "answer_yes", "sourceHandle": "true"},
        {"id": "e3", "source": "cond_1", "target": "answer_no", "sourceHandle": "false"},
        {"id": "e4", "source": "answer_yes", "target": "end_1"},
        {"id": "e5", "source": "answer_no", "target": "end_1"},
    ],
)


async def run_graph(g, inputs):
    ctx = NodeContext(db=None, run_inputs=inputs)
    engine = WorkflowEngine(g)
    return [e async for e in engine.stream(inputs, ctx)]


def test_validate_ok():
    check = WorkflowEngine(BRANCH_GRAPH).validate()
    assert check.ok, check.errors


def test_detect_cycle():
    g = graph(
        [node("start_1", "start"), node("end_1", "end")],
        [
            {"id": "e1", "source": "start_1", "target": "end_1"},
            {"id": "e2", "source": "end_1", "target": "start_1"},
        ],
    )
    check = WorkflowEngine(g).validate()
    assert not check.ok
    assert any("环" in e for e in check.errors)


def test_missing_start_reported():
    g = graph([node("end_1", "end")], [])
    check = WorkflowEngine(g).validate()
    assert not check.ok


async def test_true_branch_only():
    events = await run_graph(BRANCH_GRAPH, {"score": 88})
    completed = [e for e in events if e["event"] == "node_completed"]
    executed = [e["data"]["node_id"] for e in completed]
    assert "answer_yes" in executed
    assert "answer_no" not in executed
    final = next(e for e in events if e["event"] == "run_completed")
    assert final["data"]["outputs"]["answer"] == "及格：88"


async def test_false_branch_only():
    events = await run_graph(BRANCH_GRAPH, {"score": 40})
    executed = [e["data"]["node_id"] for e in events if e["event"] == "node_completed"]
    assert "answer_no" in executed and "answer_yes" not in executed


async def test_missing_required_input_fails():
    events = await run_graph(BRANCH_GRAPH, {})
    assert any(e["event"] == "run_error" for e in events)


def test_variable_resolution():
    ctx = {"start": {"query": "你好"}, "llm_1": {"text": "回答"}, "http_1": {"body": {"items": [{"name": "a"}]}}}
    assert render_template("{{start.query}} -> {{llm_1.text}}", ctx) == "你好 -> 回答"
    assert resolve_path(ctx, "http_1.body.items.0.name") == "a"
    with pytest.raises(KeyError):
        resolve_path(ctx, "nope.value")
    with pytest.raises(ValidationFailedError):
        render_template("{{nope.value}}", ctx, strict=True)


async def test_code_node_expression():
    g = graph(
        [
            node("start_1", "start", {"params": [{"name": "n", "type": "number", "required": True}]}),
            node("code_1", "code", {"expression": "n * 2", "output_key": "doubled"}),
            node("answer_1", "answer", {"answer": "结果 {{code_1.doubled}}"}),
            node("end_1", "end", {}),
        ],
        [
            {"id": "e1", "source": "start_1", "target": "code_1"},
            {"id": "e2", "source": "code_1", "target": "answer_1"},
            {"id": "e3", "source": "answer_1", "target": "end_1"},
        ],
    )
    events = await run_graph(g, {"n": 21})
    final = next(e for e in events if e["event"] == "run_completed")
    assert final["data"]["outputs"]["answer"] == "结果 42"
