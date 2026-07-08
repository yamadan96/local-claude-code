"""Anthropic API provider stub (future implementation)."""

from __future__ import annotations

from lcc.agent.messages import ChatRequest, ChatResponse


class AnthropicProvider:
    """Stub for future Anthropic API backend.

    Not yet implemented -- raises NotImplementedError on use.
    """

    def __init__(
        self, api_key: str = "", model: str = "claude-sonnet-4-20250514"
    ) -> None:
        self._api_key = api_key
        self._model = model

    def complete(self, request: ChatRequest) -> ChatResponse:
        """Not yet implemented."""
        raise NotImplementedError(
            "Anthropic provider is not yet implemented. "
            "Use an OpenAI-compatible provider (Ollama, LM Studio, vLLM) instead."
        )
