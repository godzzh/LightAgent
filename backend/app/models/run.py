"""Agent 运行、步骤与 LLM 调用日志。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class AgentRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    application_id: Mapped[str] = mapped_column(String(32), index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)  # running/succeeded/failed/canceled
    user_input: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(24), default="function_calling")
    model_name: Mapped[str] = mapped_column(String(120), default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    steps_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, default="")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="debug")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AgentStep(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_steps"

    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    step_type: Mapped[str] = mapped_column(String(24), default="thought")
    # thought / action / observation / final / error
    content: Mapped[str] = mapped_column(Text, default="")
    tool_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    tool_input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tool_output: Mapped[Any] = mapped_column(JSON, nullable=True)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    run: Mapped[AgentRun] = relationship(back_populates="steps")


class LlmCallLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "llm_call_logs"

    run_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    application_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    model_name: Mapped[str] = mapped_column(String(120), default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="success", index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, default="")
