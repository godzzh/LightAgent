"""工具服务：数据库工具定义 → 可执行工具实例。"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import Tool
from app.tool_registry.builtin import BUILTIN_TOOLS, ensure_builtin_registered
from app.tool_registry.custom.http_tool import ConfigurableHttpTool
from app.tool_registry.registry import BaseTool, registry


def builtin_catalog() -> list[dict[str, Any]]:
    return BUILTIN_TOOLS


async def resolve_tools(
    db: AsyncSession, tool_keys: Optional[list[str]] = None, *, workspace_id: Optional[str] = None
) -> list[BaseTool]:
    """把工具标识列表解析为可执行实例。未指定则返回全部内置工具。"""
    ensure_builtin_registered()
    keys = tool_keys if tool_keys is not None else [t["tool_key"] for t in BUILTIN_TOOLS]
    tools: list[BaseTool] = []

    builtin_map = {t["tool_key"]: t for t in BUILTIN_TOOLS}
    custom_keys: list[str] = []
    for key in keys:
        if key in builtin_map:
            inst = registry.get_tool(key)
            if inst:
                tools.append(inst)
        else:
            custom_keys.append(key)

    if custom_keys:
        stmt = select(Tool).where(Tool.tool_key.in_(custom_keys), Tool.enabled.is_(True))
        if workspace_id:
            stmt = stmt.where((Tool.workspace_id == workspace_id) | (Tool.workspace_id.is_(None)))
        for record in (await db.execute(stmt)).scalars().all():
            if record.tool_type == "http":
                tools.append(
                    ConfigurableHttpTool(
                        name=record.tool_key,
                        description=record.description or record.name,
                        parameters=record.parameters or [],
                        config=record.config or {},
                    )
                )
    return tools


async def get_tool_schema(db: AsyncSession, tool_key: str) -> Optional[dict[str, Any]]:
    ensure_builtin_registered()
    inst = registry.get_tool(tool_key)
    if inst:
        return inst.spec.to_openai_schema()
    rec = (
        await db.execute(select(Tool).where(Tool.tool_key == tool_key).limit(1))
    ).scalar_one_or_none()
    if not rec:
        return None
    return ConfigurableHttpTool(
        name=rec.tool_key, description=rec.description, parameters=rec.parameters or [], config=rec.config or {}
    ).spec.to_openai_schema()
