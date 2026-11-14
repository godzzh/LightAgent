"""内置工具：JSON 处理与文本处理。"""
from __future__ import annotations

import json
import re
from typing import Any

from app.core.exceptions import ValidationFailedError
from app.tool_registry.registry import BaseTool, ToolSpec, register


class JsonQueryTool(BaseTool):
    spec = ToolSpec(
        name="json_query",
        description="解析 JSON 字符串并按点号路径取值，例如 data.items.0.name。path 为空时返回解析后的完整 JSON。",
        parameters=[
            {"name": "json_text", "type": "string", "description": "JSON 字符串", "required": True},
            {"name": "path", "type": "string", "description": "点号路径，可为空", "required": False, "default": ""},
        ],
    )

    async def execute(self, args: dict) -> Any:
        try:
            data = json.loads(args["json_text"])
        except json.JSONDecodeError as exc:
            raise ValidationFailedError(f"JSON 解析失败: {exc}") from exc
        path = (args.get("path") or "").strip()
        if not path:
            return data
        cur = data
        for part in path.split("."):
            if isinstance(cur, list):
                try:
                    cur = cur[int(part)]
                except (ValueError, IndexError):
                    raise ValidationFailedError(f"路径不存在: {path}") from None
            elif isinstance(cur, dict):
                if part not in cur:
                    raise ValidationFailedError(f"路径不存在: {path}")
                cur = cur[part]
            else:
                raise ValidationFailedError(f"路径不可继续下探: {part}")
        return cur


class TextProcessTool(BaseTool):
    spec = ToolSpec(
        name="text_process",
        description="文本处理工具，支持统计字数、大小写转换、去空白、正则提取、截断等操作。",
        parameters=[
            {"name": "text", "type": "string", "description": "待处理文本", "required": True},
            {
                "name": "operation",
                "type": "string",
                "description": "操作类型",
                "required": True,
                "enum": ["stats", "upper", "lower", "trim", "extract", "truncate", "replace"],
            },
            {"name": "pattern", "type": "string", "description": "extract/replace 使用的正则或原文", "required": False},
            {"name": "replacement", "type": "string", "description": "replace 的替换文本", "required": False, "default": ""},
            {"name": "limit", "type": "integer", "description": "truncate 的最大长度", "required": False, "default": 200},
        ],
    )

    async def execute(self, args: dict) -> Any:
        text = args["text"]
        op = args["operation"]
        if op == "stats":
            chars = len(text)
            words = len(re.findall(r"[A-Za-z0-9_]+", text))
            cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
            lines = text.count("\n") + (1 if text else 0)
            return {"chars": chars, "words": words, "cjk_chars": cjk, "lines": lines}
        if op == "upper":
            return text.upper()
        if op == "lower":
            return text.lower()
        if op == "trim":
            return re.sub(r"\s+", " ", text).strip()
        if op == "truncate":
            limit = int(args.get("limit") or 200)
            return text[:limit] + ("..." if len(text) > limit else "")
        if op == "extract":
            pattern = args.get("pattern") or ""
            if not pattern:
                raise ValidationFailedError("extract 需要提供 pattern")
            try:
                return re.findall(pattern, text)
            except re.error as exc:
                raise ValidationFailedError(f"正则不合法: {exc}") from exc
        if op == "replace":
            pattern = args.get("pattern") or ""
            if not pattern:
                raise ValidationFailedError("replace 需要提供 pattern")
            return text.replace(pattern, args.get("replacement") or "")
        raise ValidationFailedError(f"不支持的操作: {op}")


register(JsonQueryTool())
register(TextProcessTool())
