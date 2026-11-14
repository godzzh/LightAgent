"""统一 Tool Registry。

- 元数据（name/description/parameters）与执行逻辑分离；
- 所有工具必须实现 validate() / execute()，执行统一带超时与异常捕获。
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from loguru import logger

from app.core.exceptions import AppError, NotFoundError, ValidationFailedError


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: list[dict[str, Any]] = field(default_factory=list)
    # parameters: [{name, type, description, required, default}]
    timeout: float = 20.0

    def to_openai_schema(self) -> dict[str, Any]:
        props: dict[str, Any] = {}
        required: list[str] = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.get("type", "string"), "description": p.get("description", "")}
            if p.get("enum"):
                prop["enum"] = p["enum"]
            if p.get("items"):
                prop["items"] = p["items"]
            props[p["name"]] = prop
            if p.get("required"):
                required.append(p["name"])
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        }


class BaseTool:
    spec: ToolSpec

    def validate(self, args: dict[str, Any]) -> dict[str, Any]:
        """参数校验 + 默认值填充 + 类型转换。"""
        if not isinstance(args, dict):
            raise ValidationFailedError(f"工具 {self.spec.name} 参数必须为对象")
        cleaned: dict[str, Any] = {}
        for p in self.spec.parameters:
            key = p["name"]
            val = args.get(key, p.get("default"))
            if val is None or val == "":
                if p.get("required"):
                    raise ValidationFailedError(f"缺少必填参数: {key}")
                continue
            ptype = p.get("type", "string")
            try:
                if ptype == "number":
                    val = float(val)
                elif ptype == "integer":
                    val = int(val)
                elif ptype == "boolean":
                    val = val if isinstance(val, bool) else str(val).lower() in ("1", "true", "yes")
                elif ptype == "string":
                    val = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
            except (TypeError, ValueError) as exc:
                raise ValidationFailedError(f"参数 {key} 类型应为 {ptype}") from exc
            cleaned[key] = val
        return cleaned

    async def execute(self, args: dict[str, Any]) -> Any:  # pragma: no cover - 抽象
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.spec.name] = tool

    def unregister_tool(self, name: str) -> None:
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self, names: Optional[list[str]] = None) -> list[dict[str, Any]]:
        tools = self.list_tools() if not names else [t for t in self.list_tools() if t.spec.name in names]
        return [t.spec.to_openai_schema() for t in tools]

    async def execute_tool(self, name: str, args: dict[str, Any], *, timeout: Optional[float] = None) -> Any:
        tool = self.get_tool(name)
        if not tool:
            raise NotFoundError(f"工具不存在: {name}")
        cleaned = tool.validate(args or {})
        limit = timeout or tool.spec.timeout
        try:
            result = await asyncio.wait_for(tool.execute(cleaned), timeout=limit)
            return result
        except asyncio.TimeoutError as exc:
            logger.warning(f"tool {name} timeout after {limit}s")
            raise AppError(f"工具 {name} 执行超时({limit}s)") from exc
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"tool {name} failed: {exc}")
            raise AppError(f"工具 {name} 执行失败: {exc}") from exc


registry = ToolRegistry()


def register(tool: BaseTool) -> BaseTool:
    registry.register_tool(tool)
    return tool
