"""异步数据库引擎 / Session 管理。"""
from __future__ import annotations

import json

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.is_sqlite

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
    # 中文不转义保存：既省空间，也让 JSON 字段的 contains 关键词检索可命中
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False, default=str),
    **({"connect_args": {"check_same_thread": False}} if _is_sqlite else {}),
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """开发环境自动建表（生产使用 alembic upgrade head）。"""
    from app import models  # noqa: F401  确保模型注册到 metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
