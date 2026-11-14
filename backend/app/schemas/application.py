"""应用与 Agent Schema。"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

AppType = Literal["chat_agent", "chatbot", "workflow"]


class AgentVariable(BaseModel):
    name: str
    type: str = "string"
    default: Any = None
    description: str = ""


class AgentToolRef(BaseModel):
    tool_key: str
    enabled: bool = True


class AgentConfig(BaseModel):
    """Agent 配置（存入 applications.config）。"""

    system_prompt: str = "你是一个乐于助人的 AI 助手。"
    user_prompt: str = "{{query}}"
    welcome_message: str = "你好，我是你的智能助手，有什么可以帮你？"
    opening_questions: list[str] = Field(default_factory=list)
    mode: Literal["function_calling", "react"] = "function_calling"
    model_config_id: Optional[str] = None

    temperature: float = Field(0.7, ge=0, le=2)
    top_p: float = Field(1.0, ge=0, le=1)
    max_tokens: int = Field(2048, ge=1, le=32768)
    max_steps: int = Field(8, ge=1, le=30)
    max_tool_calls: int = Field(6, ge=0, le=30)
    max_context_messages: int = Field(20, ge=0, le=100)

    enable_memory: bool = True
    enable_tools: bool = True
    enable_knowledge: bool = True

    tools: list[AgentToolRef] = Field(default_factory=list)
    dataset_ids: list[str] = Field(default_factory=list)
    knowledge_top_k: int = Field(4, ge=1, le=20)
    knowledge_threshold: float = Field(0.3, ge=0, le=1)

    variables: list[AgentVariable] = Field(default_factory=list)


class ApplicationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    icon: str = "robot"
    app_type: AppType = "chat_agent"
    template: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    model_config_id: Optional[str] = None
    workflow_id: Optional[str] = None


class ApplicationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    model_config_id: Optional[str] = None
    workflow_id: Optional[str] = None


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    stream: bool = True


class PublishRequest(BaseModel):
    api_enabled: bool = True
    create_key: bool = True
    key_name: str = "default"


class ApiKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    enabled: bool
    created_at: Any = None
