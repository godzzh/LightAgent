"""LightAgent 后端入口。"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.seed import run_seed
from app.tool_registry.builtin import ensure_builtin_registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"启动 {settings.APP_NAME}（env={settings.ENV}）")
    ensure_builtin_registered()
    await init_db()
    await run_seed()
    yield
    await engine.dispose()
    logger.info("服务已关闭")


app = FastAPI(
    title="LightAgent API",
    description="轻量级 AI Agent 开发平台 API 文档",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)

register_exception_handlers(app)

# SSE 接口需要绕过统一 JSON 包装，因此不在全局 route_class 中设置包络，
# 而是对普通接口按模块使用 EnvelopeRoute（见各 api 模块）。
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "database": "sqlite" if settings.is_sqlite else "postgresql",
        "time": int(time.time()),
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"app": settings.APP_NAME, "docs": "/docs", "api": settings.API_PREFIX}
