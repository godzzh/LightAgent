"""SSE 工具：标准事件格式 + 断连清理。"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # 关闭 nginx 缓冲
}


def sse_event(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


async def to_sse(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    """把 {"event":..., "data":...} 流转换为 SSE 文本流。"""
    try:
        async for ev in events:
            yield sse_event(ev["event"], ev.get("data") or {})
    except GeneratorExit:  # 客户端断开
        return
    finally:
        yield sse_event("stream_closed", {"ok": True})


def sse_response(events: AsyncIterator[dict[str, Any]]):
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        to_sse(events), media_type="text/event-stream", headers=SSE_HEADERS
    )
