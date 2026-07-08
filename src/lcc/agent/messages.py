"""Conversation state and message models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolCall:
    """A tool call requested by the assistant."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class TokenUsage:
    """Token usage from a provider response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatMessage:
    """A single message in the conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible API dict."""
        d: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": (
                            tc.arguments
                            if isinstance(tc.arguments, str)
                            else __import__("json").dumps(tc.arguments)
                        ),
                    },
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            d["name"] = self.name
        return d


@dataclass
class ChatRequest:
    """Request to send to a ChatProvider."""

    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    model: str = ""
    max_tokens: int | None = None


@dataclass
class ChatResponse:
    """Response from a ChatProvider."""

    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: TokenUsage | None = None


@dataclass
class ConversationState:
    """Manages the full conversation message history."""

    messages: list[ChatMessage] = field(default_factory=list)

    def append_system(self, content: str) -> None:
        """Append a system message."""
        self.messages.append(ChatMessage(role="system", content=content))

    def append_user(self, content: str) -> None:
        """Append a user message."""
        self.messages.append(ChatMessage(role="user", content=content))

    def append_assistant(
        self,
        content: str | None,
        tool_calls: list[ToolCall] | None = None,
    ) -> None:
        """Append an assistant message, optionally with tool calls."""
        self.messages.append(
            ChatMessage(role="assistant", content=content, tool_calls=tool_calls)
        )

    def append_tool_result(self, tool_call_id: str, content: str) -> None:
        """Append a tool result message."""
        self.messages.append(
            ChatMessage(role="tool", content=content, tool_call_id=tool_call_id)
        )

    def to_api_messages(self) -> list[dict[str, Any]]:
        """Convert all messages to OpenAI-compatible API dicts."""
        return [m.to_api_dict() for m in self.messages]

    def clear(self) -> None:
        """Clear all messages except system messages."""
        self.messages = [m for m in self.messages if m.role == "system"]
