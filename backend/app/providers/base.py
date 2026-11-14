"""统一 LLM Provider 抽象层。

业务层只依赖本模块定义的接口，不直接依赖任何厂商 SDK。
新增厂商只需实现 BaseLLMProvider 子类并注册到 factory。
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class ChatMessage:
    role: str  # system / user / assistant / tool
    content: str = ""
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens


@dataclass
class ChatResult:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = ""
    raw: Any = None


class ProviderError(Exception):
    """Provider 层统一异常，携带可读错误信息。"""

    def __init__(self, message: str, *, kind: str = "provider_error", status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.kind = kind  # auth / not_found / timeout / network / rate_limit / provider_error
        self.status_code = status_code


class BaseLLMProvider(abc.ABC):
    provider_type: str = "base"

    def __init__(self, *, base_url: str, api_key: str, timeout: int = 120, max_retries: int = 2):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    # ---- 子类必须实现 ----
    @abc.abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 2048,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: str = "auto",
    ) -> ChatResult: ...

    @abc.abstractmethod
    def chat_stream(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 2048,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """产出 {"type": "token"|"tool_calls"|"usage"|"done", ...} 事件。"""
        ...

    @abc.abstractmethod
    async def embed(self, model: str, texts: list[str]) -> list[list[float]]: ...

    @abc.abstractmethod
    async def validate_connection(self) -> tuple[bool, str]: ...

    async def get_models(self) -> list[str]:
        return []
