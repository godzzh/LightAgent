"""工作空间服务。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Workspace, WorkspaceMember


async def create_default_workspace(db: AsyncSession, user: User) -> Workspace:
    ws = Workspace(name=f"{user.username} 的工作空间", description="默认工作空间", owner_id=user.id)
    db.add(ws)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner"))
    await db.commit()
    await db.refresh(ws)
    return ws


async def get_user_workspace(db: AsyncSession, user: User) -> Workspace:
    """当前用户的主工作空间（多工作空间为后续扩展点）。"""
    stmt = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at.asc())
        .limit(1)
    )
    ws = (await db.execute(stmt)).scalar_one_or_none()
    if ws:
        return ws
    return await create_default_workspace(db, user)
