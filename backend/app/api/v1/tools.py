"""工具管理接口。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import Pagination, get_current_user, paginate
from app.core.exceptions import ConflictError, NotFoundError
from app.core.response import EnvelopeRoute
from app.models.tool import Tool
from app.models.user import User
from app.schemas.knowledge import ToolCreate, ToolTestRequest, ToolUpdate
from app.services.tools.tool_service import builtin_catalog, resolve_tools
from app.services.workspace_service import get_user_workspace
from app.tool_registry.custom.http_tool import ConfigurableHttpTool

router = APIRouter(route_class=EnvelopeRoute, prefix="/tools", tags=["工具管理"])


def _tool_out(t: Tool) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "tool_key": t.tool_key,
        "description": t.description,
        "tool_type": t.tool_type,
        "parameters": t.parameters or [],
        "config": t.config or {},
        "is_builtin": t.is_builtin,
        "enabled": t.enabled,
        "created_at": t.created_at,
    }


@router.get("/builtin", summary="内置工具目录")
async def builtin_tools(user: User = Depends(get_current_user)):
    return builtin_catalog()


@router.get("", summary="工具列表（内置 + 自定义）")
async def list_tools(
    keyword: str = "",
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_user_workspace(db, user)
    stmt = select(Tool).where((Tool.workspace_id == ws.id) | (Tool.workspace_id.is_(None)))
    count_stmt = select(func.count(Tool.id)).where(
        (Tool.workspace_id == ws.id) | (Tool.workspace_id.is_(None))
    )
    if keyword:
        stmt = stmt.where(Tool.name.contains(keyword) | Tool.tool_key.contains(keyword))
        count_stmt = count_stmt.where(Tool.name.contains(keyword) | Tool.tool_key.contains(keyword))
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(Tool.is_builtin.desc(), Tool.created_at.asc()).offset(p.offset).limit(p.page_size))
    ).scalars().all()
    return paginate([_tool_out(t) for t in rows], int(total), p)


@router.post("", summary="创建自定义 HTTP 工具")
async def create_tool(
    payload: ToolCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_user_workspace(db, user)
    dup = (
        await db.execute(select(Tool).where(Tool.tool_key == payload.tool_key, Tool.workspace_id == ws.id))
    ).scalar_one_or_none()
    if dup:
        raise ConflictError("工具标识已存在")
    if not payload.config.get("url"):
        raise ConflictError("请配置请求地址")

    tool = Tool(
        workspace_id=ws.id,
        name=payload.name,
        tool_key=payload.tool_key,
        description=payload.description,
        tool_type="http",
        parameters=[p.model_dump() for p in payload.parameters],
        config=payload.config,
        is_builtin=False,
        enabled=payload.enabled,
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return _tool_out(tool)


@router.get("/{tool_id}", summary="工具详情")
async def get_tool(
    tool_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    tool = await db.get(Tool, tool_id)
    if not tool:
        raise NotFoundError("工具不存在")
    return _tool_out(tool)


@router.patch("/{tool_id}", summary="更新工具")
async def update_tool(
    tool_id: str,
    payload: ToolUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tool = await db.get(Tool, tool_id)
    if not tool:
        raise NotFoundError("工具不存在")
    if tool.is_builtin:
        raise ConflictError("内置工具不可修改")
    data = payload.model_dump(exclude_unset=True)
    if "parameters" in data and data["parameters"] is not None:
        data["parameters"] = [p if isinstance(p, dict) else p.model_dump() for p in data["parameters"]]
    for k, v in data.items():
        if v is not None:
            setattr(tool, k, v)
    await db.commit()
    await db.refresh(tool)
    return _tool_out(tool)


@router.delete("/{tool_id}", summary="删除工具")
async def delete_tool(
    tool_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    tool = await db.get(Tool, tool_id)
    if not tool:
        raise NotFoundError("工具不存在")
    if tool.is_builtin:
        raise ConflictError("内置工具不可删除")
    await db.delete(tool)
    await db.commit()
    return {"ok": True}


@router.post("/{tool_id}/test", summary="测试工具执行")
async def test_tool(
    tool_id: str,
    payload: ToolTestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tool = await db.get(Tool, tool_id)
    if not tool:
        raise NotFoundError("工具不存在")
    instance = ConfigurableHttpTool(
        name=tool.tool_key,
        description=tool.description,
        parameters=tool.parameters or [],
        config=tool.config or {},
    )
    cleaned = instance.validate(payload.arguments)
    result = await instance.execute(cleaned)
    return {"arguments": cleaned, "result": result}


@router.post("/builtin/{tool_key}/test", summary="测试内置工具")
async def test_builtin_tool(
    tool_key: str,
    payload: ToolTestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tools = await resolve_tools(db, [tool_key])
    if not tools:
        raise NotFoundError("工具不存在")
    instance = tools[0]
    cleaned = instance.validate(payload.arguments)
    result = await instance.execute(cleaned)
    return {"arguments": cleaned, "result": result}
