"""知识库、工具与工作流 Schema。"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    embedding_model_id: Optional[str] = None
    chunk_size: int = Field(500, ge=50, le=4000)
    chunk_overlap: int = Field(50, ge=0, le=1000)
    split_strategy: Literal["fixed", "paragraph", "heading", "separator"] = "fixed"
    separator: str = "\n\n"
    keep_heading: bool = True
    clean_whitespace: bool = True


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    embedding_model_id: Optional[str] = None
    chunk_size: Optional[int] = Field(None, ge=50, le=4000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1000)
    split_strategy: Optional[Literal["fixed", "paragraph", "heading", "separator"]] = None
    separator: Optional[str] = None
    keep_heading: Optional[bool] = None
    clean_whitespace: Optional[bool] = None


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    dataset_ids: Optional[list[str]] = None
    top_k: int = Field(4, ge=1, le=20)
    threshold: float = Field(0.3, ge=0, le=1)


class SegmentUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class ToolParam(BaseModel):
    name: str
    type: Literal["string", "number", "integer", "boolean"] = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    location: Literal["query", "body", "path"] = "query"


class ToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    tool_key: str = Field(..., min_length=1, max_length=60, pattern="^[a-zA-Z_][a-zA-Z0-9_]*$")
    description: str = ""
    tool_type: Literal["http"] = "http"
    parameters: list[ToolParam] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[list[ToolParam]] = None
    config: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class ToolTestRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    graph: Optional[dict[str, Any]] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    graph: Optional[dict[str, Any]] = None


class WorkflowRunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    stream: bool = True
