"""Client for communicating with a locally hosted LM Studio instance."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx


class LMStudioClient:
    """Minimal async client for LM Studio's OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        default_headers = {"Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)
        self._client = httpx.AsyncClient(base_url=self._base_url, headers=default_headers, timeout=timeout)

    @property
    def model(self) -> str:
        return self._model

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        temperature: float = 0.1,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant's message content."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": list(messages),
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("LM Studio returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("LM Studio response missing content")
        return content


__all__ = ["LMStudioClient"]
