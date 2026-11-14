"""可配置 HTTP 工具：把用户定义的表单转换为 Function Calling 工具并执行。

执行前统一做 SSRF 校验；带超时与错误包装。
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from app.core.exceptions import AppError, ValidationFailedError
from app.tool_registry.registry import BaseTool, ToolSpec
from app.utils.net import validate_public_url

_TEMPLATE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


def _render(template: Any, args: dict[str, Any]) -> Any:
    """把 {{var}} 占位符替换为参数值；支持嵌套 dict / list。"""
    if isinstance(template, str):
        def repl(m: re.Match) -> str:
            key = m.group(1)
            val = args.get(key.split(".")[-1], args.get(key, ""))
            return str(val) if val is not None else ""

        stripped = template.strip()
        # 整个字符串就是一个占位符时保留原始类型
        if _TEMPLATE_RE.fullmatch(stripped):
            key = _TEMPLATE_RE.findall(stripped)[0].split(".")[-1]
            return args.get(key, "")
        return _TEMPLATE_RE.sub(repl, template)
    if isinstance(template, dict):
        return {k: _render(v, args) for k, v in template.items()}
    if isinstance(template, list):
        return [_render(v, args) for v in template]
    return template


class ConfigurableHttpTool(BaseTool):
    def __init__(self, *, name: str, description: str, parameters: list[dict], config: dict):
        cfg = config or {}
        self.config = cfg
        self.spec = ToolSpec(
            name=name,
            description=description or name,
            parameters=parameters or [],
            timeout=float(cfg.get("timeout", 20)),
        )

    async def execute(self, args: dict) -> Any:
        cfg = self.config
        url = _render(cfg.get("url", ""), args)
        if not isinstance(url, str):
            url = str(url)
        url = validate_public_url(url)
        method = str(cfg.get("method", "GET")).upper()

        headers = _render(cfg.get("headers") or {}, args)
        query = _render(cfg.get("query") or {}, args)
        body_tpl = cfg.get("body")
        body = _render(body_tpl, args) if body_tpl not in (None, "", {}) else None

        try:
            async with httpx.AsyncClient(timeout=self.spec.timeout, follow_redirects=False) as client:
                resp = await client.request(
                    method,
                    url,
                    params=query or None,
                    headers={k: str(v) for k, v in (headers or {}).items()},
                    json=body if isinstance(body, (dict, list)) else None,
                    content=body if isinstance(body, str) else None,
                )
        except httpx.TimeoutException as exc:
            raise AppError(f"HTTP 请求超时({self.spec.timeout}s)") from exc
        except httpx.HTTPError as exc:
            raise AppError(f"HTTP 请求失败: {exc}") from exc

        text = resp.text
        try:
            parsed: Optional[Any] = resp.json()
        except (json.JSONDecodeError, ValueError):
            parsed = None
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "json": parsed,
            "text": text[:8000],
        }


class SimpleHttpTool(BaseTool):
    """内置通用 HTTP 请求工具（GET/POST 任意地址，带 SSRF 防护）。"""

    spec = ToolSpec(
        name="http_request",
        description="向指定的公网 HTTP 接口发起请求并返回响应内容，支持 GET/POST 等方法。",
        parameters=[
            {"name": "url", "type": "string", "description": "完整 URL（仅公网地址）", "required": True},
            {
                "name": "method",
                "type": "string",
                "description": "请求方法",
                "required": False,
                "default": "GET",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            },
            {"name": "headers", "type": "string", "description": "请求头 JSON 字符串", "required": False},
            {"name": "body", "type": "string", "description": "请求体 JSON 字符串", "required": False},
        ],
        timeout=25,
    )

    async def execute(self, args: dict) -> Any:
        cfg = {
            "url": args["url"],
            "method": args.get("method", "GET"),
            "headers": json.loads(args["headers"]) if args.get("headers") else {},
            "body": json.loads(args["body"]) if args.get("body") else None,
            "timeout": 25,
        }
        return await ConfigurableHttpTool(
            name=self.spec.name, description="", parameters=[], config=cfg
        ).execute({})
