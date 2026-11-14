"""模型供应商与模型配置。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class ModelProvider(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "model_providers"

    name: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(32), default="deepseek", index=True)
    base_url: Mapped[str] = mapped_column(String(255), default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, default="")

    configs: Mapped[list["ModelConfig"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class ModelConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "model_configs"

    provider_id: Mapped[str] = mapped_column(
        ForeignKey("model_providers.id", ondelete="CASCADE"), index=True
    )
    display_name: Mapped[str] = mapped_column(String(120))
    model_name: Mapped[str] = mapped_column(String(120))
    model_type: Mapped[str] = mapped_column(String(16), default="llm")  # llm / embedding / rerank
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    top_p: Mapped[float] = mapped_column(Float, default=1.0)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    context_window: Mapped[int] = mapped_column(Integer, default=32768)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_tool_call: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, default="")

    provider: Mapped[ModelProvider] = relationship(back_populates="configs")
