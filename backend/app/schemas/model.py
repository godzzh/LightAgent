"""模型管理 Schema。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    provider_type: str = "deepseek"
    base_url: str = ""
    api_key: str = ""
    enabled: bool = True
    is_default: bool = False
    remark: str = ""


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(None, description="留空表示不修改")
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    remark: Optional[str] = None


class ModelConfigCreate(BaseModel):
    provider_id: str
    display_name: str = Field(..., min_length=1, max_length=120)
    model_name: str = Field(..., min_length=1, max_length=120)
    model_type: str = Field("llm", pattern="^(llm|embedding|rerank)$")
    temperature: float = Field(0.7, ge=0, le=2)
    top_p: float = Field(1.0, ge=0, le=1)
    max_tokens: int = Field(2048, ge=1, le=32768)
    context_window: int = Field(32768, ge=1)
    supports_streaming: bool = True
    supports_tool_call: bool = True
    is_default: bool = False
    enabled: bool = True
    remark: str = ""


class ModelConfigUpdate(BaseModel):
    display_name: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    max_tokens: Optional[int] = Field(None, ge=1, le=32768)
    context_window: Optional[int] = None
    supports_streaming: Optional[bool] = None
    supports_tool_call: Optional[bool] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None
    remark: Optional[str] = None


class TestConnectionRequest(BaseModel):
    provider_id: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
