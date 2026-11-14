"""内置工具注册入口。首次导入即完成注册。"""
from __future__ import annotations

from typing import Any

from app.tool_registry.builtin import data_tools, math_tools, system_tools  # noqa: F401
from app.tool_registry.custom.http_tool import SimpleHttpTool
from app.tool_registry.registry import BaseTool, registry

BUILTIN_TOOLS: list[dict[str, Any]] = [
    {
        "name": "当前时间",
        "tool_key": "current_time",
        "description": "获取当前日期、时间、星期与时区信息。",
        "parameters": system_tools.CurrentTimeTool.spec.parameters,
    },
    {
        "name": "日期计算",
        "tool_key": "date_calc",
        "description": "按天数偏移计算日期，或计算两个日期相差天数。",
        "parameters": system_tools.DateCalcTool.spec.parameters,
    },
    {
        "name": "数学计算",
        "tool_key": "math_calc",
        "description": "安全计算数学表达式（支持 sqrt/log/sin 等函数）。",
        "parameters": math_tools.MathCalcTool.spec.parameters,
    },
    {
        "name": "HTTP 请求",
        "tool_key": "http_request",
        "description": "向公网 HTTP 接口发起请求（带 SSRF 防护）。",
        "parameters": SimpleHttpTool.spec.parameters,
    },
    {
        "name": "JSON 解析",
        "tool_key": "json_query",
        "description": "解析 JSON 字符串并按路径取值。",
        "parameters": data_tools.JsonQueryTool.spec.parameters,
    },
    {
        "name": "文本处理",
        "tool_key": "text_process",
        "description": "文本统计、大小写、去空白、正则提取、截断与替换。",
        "parameters": data_tools.TextProcessTool.spec.parameters,
    },
]


def ensure_builtin_registered() -> None:
    if not registry.get_tool("http_request"):
        registry.register_tool(SimpleHttpTool())


def get_tool_instance(name: str) -> BaseTool | None:
    ensure_builtin_registered()
    return registry.get_tool(name)
