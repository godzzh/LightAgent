"""Agent Runtime 测试：使用可编排的假 Provider，验证流式输出、工具调用与资源限制。"""
from __future__ import annotations

import pytest

from app.engines.agent_runtime import AgentRuntime, AgentRuntimeConfig
from app.providers.base import BaseLLMProvider, ChatResult, Usage
from app.tool_registry.registry import BaseTool, ToolSpec


class FakeProvider(BaseLLMProvider):
    """按脚本依次返回预设事件的假模型。"""

    provider_type = "fake"

    def __init__(self, script: list[list[dict]]):
        super().__init__(base_url="", api_key="")
        self.script = script
        self.calls = 0

    async def chat(self, model, messages, **kwargs) -> ChatResult:
        return ChatResult(content="unused")

    async def chat_stream(self, model, messages, **kwargs):
        events = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        for ev in events:
            yield ev

    async def embed(self, model, texts):
        return [[0.0] for _ in texts]

    async def validate_connection(self):
        return True, "ok"


class EchoTool(BaseTool):
    spec = ToolSpec(
        name="echo",
        description="原样返回输入",
        parameters=[{"name": "text", "type": "string", "description": "文本", "required": True}],
    )

    async def execute(self, args):
        return {"echo": args["text"]}


def _collect(events):
    return [(e["event"], e["data"]) for e in events]


async def test_stream_tokens_and_completion():
    provider = FakeProvider(
        [[{"type": "token", "content": "你好"}, {"type": "token", "content": "，世界"},
          {"type": "usage", "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}},
          {"type": "done", "finish_reason": "stop"}]]
    )
    runtime = AgentRuntime(provider=provider, model_name="fake-1", config=AgentRuntimeConfig())
    events = [e async for e in runtime.stream("hi")]
    names = [e["event"] for e in events]
    assert "run_started" in names
    assert names[-1] == "run_completed"
    assert runtime.state.output == "你好，世界"
    assert runtime.state.usage.total_tokens == 8


async def test_function_calling_triggers_tool():
    provider = FakeProvider(
        [
            [{"type": "tool_calls", "tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "abc"}}]},
             {"type": "usage", "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
             {"type": "done", "finish_reason": "tool_calls"}],
            [{"type": "token", "content": "工具结果已处理"},
             {"type": "usage", "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
             {"type": "done", "finish_reason": "stop"}],
        ]
    )
    runtime = AgentRuntime(
        provider=provider,
        model_name="fake-1",
        config=AgentRuntimeConfig(max_steps=3),
        tools=[EchoTool()],
    )
    events = [e async for e in runtime.stream("调用工具")]
    kinds = [e["event"] for e in events]
    assert "tool_call" in kinds and "tool_result" in kinds
    tool_result = next(e for e in events if e["event"] == "tool_result")
    assert tool_result["data"]["output"] == {"echo": "abc"}
    assert runtime.state.tool_calls == 1
    assert runtime.state.output == "工具结果已处理"


async def test_max_steps_limit():
    # 模型永远要求调用工具，验证不会无限循环
    loop_events = [
        {"type": "tool_calls", "tool_calls": [{"id": "c", "name": "echo", "arguments": {"text": "x"}}]},
        {"type": "usage", "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
        {"type": "done", "finish_reason": "tool_calls"},
    ]
    provider = FakeProvider([loop_events])
    runtime = AgentRuntime(
        provider=provider,
        model_name="fake-1",
        config=AgentRuntimeConfig(max_steps=3, max_tool_calls=10),
        tools=[EchoTool()],
    )
    async for _ in runtime.stream("loop"):
        pass
    assert provider.calls == 3
    assert runtime.state.tool_calls <= 3


async def test_react_mode_parses_action():
    provider = FakeProvider(
        [
            [{"type": "token", "content": 'Thought: 需要调用工具\nAction: echo\nAction Input: {"text": "hi"}'},
             {"type": "usage", "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
             {"type": "done", "finish_reason": "stop"}],
            [{"type": "token", "content": "Thought: 完成\nFinal Answer: 结果已返回"},
             {"type": "usage", "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
             {"type": "done", "finish_reason": "stop"}],
        ]
    )
    runtime = AgentRuntime(
        provider=provider,
        model_name="fake-1",
        config=AgentRuntimeConfig(mode="react", max_steps=4),
        tools=[EchoTool()],
    )
    async for _ in runtime.stream("react 问题"):
        pass
    assert runtime.state.tool_calls == 1
    assert runtime.state.output == "结果已返回"
