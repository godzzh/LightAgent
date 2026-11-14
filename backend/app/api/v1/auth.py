"""认证接口：注册 / 登录 / 当前用户。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.response import EnvelopeRoute
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UpdateProfileRequest
from app.services.workspace_service import create_default_workspace, get_user_workspace

router = APIRouter(route_class=EnvelopeRoute, prefix="/auth", tags=["认证"])


@router.post("/register", summary="注册账号（同时创建默认工作空间）")
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    exists = (
        await db.execute(
            select(User).where(or_(User.email == payload.email, User.username == payload.username))
        )
    ).scalar_one_or_none()
    if exists:
        raise ConflictError("用户名或邮箱已被注册")

    # 首个用户自动成为超级管理员
    total = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    user = User(
        username=payload.username,
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        is_superuser=total is None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    ws = await create_default_workspace(db, user)
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "email": user.email},
        "workspace": {"id": ws.id, "name": ws.name},
    }


@router.post("/login", summary="登录")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(
            select(User).where(
                or_(User.username == payload.account, User.email == payload.account)
            )
        )
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("用户名或密码错误")
    if not user.is_active:
        raise UnauthorizedError("账号已被禁用")

    ws = await get_user_workspace(db, user)
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser,
        },
        "workspace": {"id": ws.id, "name": ws.name, "description": ws.description},
    }


@router.get("/me", summary="当前登录用户")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await get_user_workspace(db, user)
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
        },
        "workspace": {"id": ws.id, "name": ws.name, "description": ws.description},
    }


@router.patch("/me", summary="更新个人资料")
async def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.username:
        user.username = payload.username
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    await db.commit()
    return {"id": user.id, "username": user.username, "email": user.email}


@router.post("/logout", summary="退出登录（前端清理 Token）")
async def logout(user: User = Depends(get_current_user)):
    return {"ok": True}
