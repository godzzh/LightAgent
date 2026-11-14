"""知识库 / 文档 / 切片。"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Dataset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "datasets"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    embedding_model_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("model_configs.id", ondelete="SET NULL"), nullable=True
    )
    # 切片策略
    chunk_size: Mapped[int] = mapped_column(Integer, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50)
    split_strategy: Mapped[str] = mapped_column(String(24), default="fixed")
    separator: Mapped[str] = mapped_column(Text, default="\n\n")
    keep_heading: Mapped[bool] = mapped_column(default=True)
    clean_whitespace: Mapped[bool] = mapped_column(default=True)
    index_status: Mapped[str] = mapped_column(String(16), default="empty")  # empty/indexing/ready/failed
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    segment_count: Mapped[int] = mapped_column(Integer, default=0)

    documents: Mapped[list["Document"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(16))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="waiting", index=True)
    # waiting/parsing/splitting/indexing/completed/failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, default="")
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    dataset: Mapped[Dataset] = relationship(back_populates="documents")
    segments: Mapped[list["DocumentSegment"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentSegment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_segments"

    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    heading: Mapped[Optional[str]] = mapped_column(String(255), default="")
    # 向量以 float 列表存储：Postgres 下由 pgvector 扩展写入 vector 列，
    # 本地 SQLite 回退为 JSON + 内存余弦相似度（见 services/knowledge/vector_store.py）
    embedding: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    document: Mapped[Document] = relationship(back_populates="segments")
