"""OpenAI 协议兼容 Provider（DeepSeek / OpenAI / 任意兼容网关共用）。"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

from app.providers.base import (
    BaseLLMProvider,
    ChatMessage,
    ChatResult,
    ProviderError,
    ToolCall,
    Usage,
)


def _map_error(exc: Exception) -> ProviderError:
    if isinstance(exc, AuthenticationError):
        return ProviderError("API Key 无效或未授权", kind="auth", status_code=401)
    if isinstance(exc, NotFoundError):
        return ProviderError("模型不存在或接口地址不正确", kind="not_found", status_code=404)
    if isinstance(exc, RateLimitError):
        return ProviderError("触发了上游频率限制，请稍后重试", kind="rate_limit", status_code=429)
    if isinstance(exc, APITimeoutError):
        return ProviderError("模型调用超时", kind="timeout", status_code=504)
    if isinstance(exc, APIConnectionError):
        return ProviderError("无法连接模型服务，请检查 Base URL 与网络", kind="network", status_code=502)
    if isinstance(exc, APIStatusError):
        return ProviderError(f"模型服务返回错误({exc.status_code}): {exc.message}", kind="provider_error")
    return ProviderError(f"模型调用失败: {exc}", kind="provider_error")


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_type = "openai_compatible"
    default_base_url = "https://api.openai.com/v1"

    def _client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=self.api_key or "sk-placeholder",
            base_url=self.base_url or self.default_base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    # ------------------------------------------------------------------ chat
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
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        try:
            async with self._client() as client:
                resp = await client.chat.completions.create(**payload)
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc) from exc

        choice = resp.choices[0]
        usage = Usage(
            prompt_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(resp.usage, "total_tokens", 0) or 0,
        )
        tool_calls: list[ToolCall] = []
        for tc in choice.message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"__raw__": tc.function.arguments}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return ChatResult(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.finish_reason or "",
        )

    # ------------------------------------------------------------- chat_stream
    async def chat_stream(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 2048,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools

        buffered_calls: dict[int, dict[str, Any]] = {}
        usage = Usage()
        finish_reason = ""
        try:
            async with self._client() as client:
                try:
                    stream = await client.chat.completions.create(**payload)
                except APIStatusError:
                    # 部分兼容网关不支持 stream_options
                    payload.pop("stream_options", None)
                    stream = await client.chat.completions.create(**payload)

                async for chunk in stream:
                    if getattr(chunk, "usage", None):
                        usage = Usage(
                            prompt_tokens=chunk.usage.prompt_tokens or 0,
                            completion_tokens=chunk.usage.completion_tokens or 0,
                            total_tokens=chunk.usage.total_tokens or 0,
                        )
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    finish_reason = choice.finish_reason or finish_reason
                    delta = choice.delta
                    if getattr(delta, "content", None):
                        yield {"type": "token", "content": delta.content}
                    for tc in getattr(delta, "tool_calls", None) or []:
                        slot = buffered_calls.setdefault(
                            tc.index, {"id": "", "name": "", "arguments": ""}
                        )
                        if tc.id:
                            slot["id"] = tc.id
                        if tc.function and tc.function.name:
                            slot["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            slot["arguments"] += tc.function.arguments
        except (httpx.HTTPError, Exception) as exc:  # noqa: BLE001
            mapped = _map_error(exc)
            if isinstance(exc, ProviderError):
                raise
            raise mapped from exc

        calls: list[dict[str, Any]] = []
        for idx in sorted(buffered_calls):
            slot = buffered_calls[idx]
            try:
                args = json.loads(slot["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {"__raw__": slot["arguments"]}
            calls.append({"id": slot["id"] or f"call_{idx}", "name": slot["name"], "arguments": args})
        if calls:
            yield {"type": "tool_calls", "tool_calls": calls}
        yield {"type": "usage", "usage": usage.__dict__}
        yield {"type": "done", "finish_reason": finish_reason}

    # ----------------------------------------------------------------- embed
    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with self._client() as client:
                resp = await client.embeddings.create(model=model, input=texts)
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc) from exc
        data = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in data]

    # ------------------------------------------------------- validate / models
    async def validate_connection(self) -> tuple[bool, str]:
        try:
            async with self._client() as client:
                await client.models.list()
            return True, "连接成功"
        except Exception as exc:  # noqa: BLE001
            # 部分兼容服务未实现 /models，退化为最小对话探测
            try:
                await self.chat(
                    model="_probe_",
                    messages=[ChatMessage(role="user", content="ping")],
                    max_tokens=1,
                )
                return True, "连接成功"
            except ProviderError as perr:
                if perr.kind == "not_found":
                    return True, "接口可访问（模型探测未通过，请确认模型名称）"
                return False, perr.message

    async def get_models(self) -> list[str]:
        try:
            async with self._client() as client:
                resp = await client.models.list()
            return [m.id for m in resp.data]
        except Exception:  # noqa: BLE001
            return []
