"""FastAPI 依赖：当前用户、分页等。"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.models.user import User


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("未登录或登录已过期")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if not payload or not payload.get("sub"):
        raise UnauthorizedError("登录凭证无效")
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise UnauthorizedError("用户不存在或已被禁用")
    return user


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate(items, total: int, p: Pagination) -> dict:
    return {"items": items, "total": total, "page": p.page, "page_size": p.page_size}
