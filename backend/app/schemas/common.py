"""通用 Schema。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PageQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class OkResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None
    request_id: Optional[str] = None
