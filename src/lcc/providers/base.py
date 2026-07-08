"""ChatProvider protocol and shared types."""

from __future__ import annotations

from typing import Any, Protocol

from lcc.agent.messages import ChatRequest, ChatResponse


class ChatProvider(Protocol):
    """Protocol for LLM provider backends."""

    def complete(self, request: ChatRequest) -> ChatResponse:
        """Send a chat completion request and return the response."""
        ...


def build_tool_schemas(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure tool schemas are in the expected OpenAI function-calling format."""
    return tools
