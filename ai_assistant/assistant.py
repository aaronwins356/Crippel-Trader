"""Stub for future AI assistant integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class MessageProvider(Protocol):
    """Protocol for retrieving messages from an LLM."""

    def get_response(self, prompt: str) -> str:
        """Return a response to the provided prompt."""


@dataclass
class Assistant:
    """Placeholder assistant that echoes prompts."""

    provider: MessageProvider | None = None

    def respond(self, prompt: str) -> str:
        """Return a response from the provider or echo the prompt."""

        if self.provider is not None:
            return self.provider.get_response(prompt)
        return f"Assistant stub: {prompt}"


__all__ = ["Assistant", "MessageProvider"]
