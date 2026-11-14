"""应用 / 版本 / 会话 / 消息 / API Key。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Application(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "applications"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(64), default="robot")
    app_type: Mapped[str] = mapped_column(String(24), default="chat_agent", index=True)
    # chat_agent / chatbot / workflow
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)  # draft / published
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    model_config_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("model_configs.id", ondelete="SET NULL"), nullable=True
    )
    workflow_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    api_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)

    versions: Mapped[list["ApplicationVersion"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationVersion(Base, UUIDMixin, TimestampMixin):
    """应用配置快照，用于发布与回滚。"""

    __tablename__ = "application_versions"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    note: Mapped[Optional[str]] = mapped_column(Text, default="")

    application: Mapped[Application] = relationship(back_populates="versions")


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255), default="新会话")
    source: Mapped[str] = mapped_column(String(16), default="debug")  # debug / api

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user / assistant / system / tool
    content: Mapped[str] = mapped_column(Text, default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ApiKey(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_keys"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64), default="default")
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
