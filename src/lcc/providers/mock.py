"""Deterministic scripted provider for tests."""

from __future__ import annotations

from lcc.agent.messages import ChatRequest, ChatResponse


class MockProviderExhausted(Exception):
    """Raised when all scripted responses have been consumed."""


class MockProvider:
    """A test provider that returns pre-scripted responses in order.

    Pops responses from a queue; raises MockProviderExhausted if the queue
    is empty when complete() is called.
    """

    def __init__(self, responses: list[ChatResponse]) -> None:
        self._responses = list(responses)
        self._call_count = 0
        self._requests: list[ChatRequest] = []

    def complete(self, request: ChatRequest) -> ChatResponse:
        """Return the next scripted response."""
        self._requests.append(request)
        if not self._responses:
            raise MockProviderExhausted(
                f"MockProvider exhausted after {self._call_count} calls. "
                f"No more scripted responses available."
            )
        self._call_count += 1
        return self._responses.pop(0)

    @property
    def call_count(self) -> int:
        """Number of complete() calls made."""
        return self._call_count

    @property
    def requests(self) -> list[ChatRequest]:
        """All requests received (for assertion in tests)."""
        return self._requests
