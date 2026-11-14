"""统一响应封装：通过自定义 APIRoute 自动包装为 {code,message,data,request_id}。

实现方式：截获普通 JSON 响应体并包裹；SSE（text/event-stream）与其他二进制响应原样透传。
异常响应由全局异常处理器负责，不受此处影响。
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute

_JSON_TYPES = ("application/json",)


def ok(data: Any = None) -> dict[str, Any]:
    return {"code": 0, "message": "success", "data": data}


class EnvelopeRoute(APIRoute):
    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            response = await original_handler(request)
            ctype = response.headers.get("content-type", "")
            if not any(t in ctype for t in _JSON_TYPES):
                return response  # SSE / 文件下载等原样返回
            if response.status_code >= 400:
                return response
            body = getattr(response, "body", b"")
            if not body:
                return response
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return response
            if isinstance(data, dict) and {"code", "message"} <= set(data.keys()):
                return response  # 已是统一结构
            payload = {
                "code": 0,
                "message": "success",
                "data": data,
                "request_id": getattr(request.state, "request_id", ""),
            }
            return Response(
                content=json.dumps(payload, ensure_ascii=False, default=str),
                media_type="application/json",
                status_code=response.status_code,
            )

        return custom_handler
