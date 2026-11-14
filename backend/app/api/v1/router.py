"""v1 路由汇总。"""
from fastapi import APIRouter

from app.api.v1 import agent, applications, auth, dashboard, knowledge, logs, models, public, tools, workflows

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(applications.router)
api_router.include_router(agent.router)
api_router.include_router(models.router)
api_router.include_router(knowledge.router)
api_router.include_router(tools.router)
api_router.include_router(workflows.router)
api_router.include_router(logs.router)
api_router.include_router(public.router)
