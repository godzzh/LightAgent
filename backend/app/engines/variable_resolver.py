"""变量解析：支持 {{node_id.field}} 形式的模板引用。"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.core.exceptions import ValidationFailedError

VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_][a-zA-Z0-9_.\-\[\]]*)\s*\}\}")


def resolve_path(context: dict[str, Any], path: str) -> Any:
    """按点号路径从上下文取值，支持 list 下标，例如 llm_1.text / http_1.body.items.0.name。"""
    cur: Any = context
    for raw in path.split("."):
        part = raw.strip()
        if not part:
            continue
        # 支持 arr[0] 形式
        index: Optional[int] = None
        m = re.fullmatch(r"([^\[\]]+)\[(\d+)\]", part)
        if m:
            part, index = m.group(1), int(m.group(2))
        if isinstance(cur, dict):
            if part not in cur:
                raise KeyError(path)
            cur = cur[part]
        elif isinstance(cur, list):
            if part.isdigit():
                cur = cur[int(part)]
            else:
                raise KeyError(path)
        else:
            raise KeyError(path)
        if index is not None:
            if not isinstance(cur, list) or index >= len(cur):
                raise KeyError(path)
            cur = cur[index]
    return cur


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, default=str)


def render_template(
    template: str,
    context: dict[str, Any],
    *,
    strict: bool = False,
    keep_unknown: bool = True,
) -> str:
    """渲染模板。strict=True 时未定义变量抛错，否则保留占位符或置空。"""
    if not template:
        return ""

    def repl(match: re.Match) -> str:
        path = match.group(1)
        try:
            return _stringify(resolve_path(context, path))
        except KeyError:
            if strict:
                raise ValidationFailedError(f"变量未定义: {path}") from None
            return match.group(0) if keep_unknown else ""

    return VAR_RE.sub(repl, template)


def extract_variables(template: str) -> list[str]:
    """提取模板中的变量名（去重、保序）。用于 Prompt 变量自动识别。"""
    seen: list[str] = []
    for m in VAR_RE.finditer(template or ""):
        name = m.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def deep_render(value: Any, context: dict[str, Any], *, strict: bool = False) -> Any:
    """递归渲染 dict / list 中的字符串模板，保留非字符串原值类型。"""
    if isinstance(value, str):
        # 整个字符串为单一变量时保留原始类型（数字/对象）
        m = VAR_RE.fullmatch(value.strip())
        if m:
            try:
                return resolve_path(context, m.group(1))
            except KeyError:
                if strict:
                    raise ValidationFailedError(f"变量未定义: {m.group(1)}") from None
                return value
        return render_template(value, context, strict=strict)
    if isinstance(value, dict):
        return {k: deep_render(v, context, strict=strict) for k, v in value.items()}
    if isinstance(value, list):
        return [deep_render(v, context, strict=strict) for v in value]
    return value
