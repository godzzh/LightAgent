"""初始化数据：内置工具入库、首个管理员账号。"""
from __future__ import annotations

from loguru import logger
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.tool import Tool
from app.models.user import User
from app.services.workspace_service import create_default_workspace
from app.tool_registry.builtin import BUILTIN_TOOLS

DEFAULT_ADMIN = {"username": "admin", "email": "admin@lightagent.local", "password": "admin123"}


async def seed_builtin_tools() -> None:
    async with SessionLocal() as db:
        existing = {
            t.tool_key
            for t in (await db.execute(select(Tool).where(Tool.is_builtin.is_(True)))).scalars().all()
        }
        added = 0
        for item in BUILTIN_TOOLS:
            if item["tool_key"] in existing:
                continue
            db.add(
                Tool(
                    workspace_id=None,
                    name=item["name"],
                    tool_key=item["tool_key"],
                    description=item["description"],
                    tool_type="builtin",
                    parameters=item["parameters"],
                    config={},
                    is_builtin=True,
                    enabled=True,
                )
            )
            added += 1
        if added:
            await db.commit()
            logger.info(f"seeded {added} builtin tools")


async def seed_admin() -> None:
    async with SessionLocal() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if user:
            return
        admin = User(
            username=DEFAULT_ADMIN["username"],
            email=DEFAULT_ADMIN["email"],
            hashed_password=hash_password(DEFAULT_ADMIN["password"]),
            is_superuser=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        await create_default_workspace(db, admin)
        logger.warning(
            f"创建默认管理员: {DEFAULT_ADMIN['username']} / {DEFAULT_ADMIN['password']}（请登录后立即修改密码）"
        )


async def run_seed() -> None:
    await seed_builtin_tools()
    await seed_admin()
