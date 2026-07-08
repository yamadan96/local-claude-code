"""Tests for context trimming."""

from __future__ import annotations

from lcc.agent.context import ContextManager
from lcc.agent.messages import ChatMessage


class TestContextManager:
    def test_no_trimming_within_budget(self) -> None:
        cm = ContextManager(max_input_tokens=100000)
        messages = [
            ChatMessage(role="system", content="You are helpful."),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
        ]
        trimmed = cm.trim(messages)
        assert len(trimmed) == 3

    def test_system_messages_always_kept(self) -> None:
        cm = ContextManager(max_input_tokens=50)
        messages = [
            ChatMessage(role="system", content="System prompt."),
            ChatMessage(role="user", content="Q1 " * 100),
            ChatMessage(role="assistant", content="A1 " * 100),
            ChatMessage(role="user", content="Q2 " * 100),
            ChatMessage(role="assistant", content="A2 " * 100),
        ]
        trimmed = cm.trim(messages)
        # System should always be present
        system_msgs = [m for m in trimmed if m.role == "system"]
        assert len(system_msgs) == 1
        assert system_msgs[0].content == "System prompt."

    def test_oldest_groups_dropped_first(self) -> None:
        cm = ContextManager(max_input_tokens=200)
        messages = [
            ChatMessage(role="system", content="sys"),
            ChatMessage(role="user", content="old question " * 20),
            ChatMessage(role="assistant", content="old answer " * 20),
            ChatMessage(role="user", content="new question"),
            ChatMessage(role="assistant", content="new answer"),
        ]
        trimmed = cm.trim(messages)
        # The newest messages should be kept, oldest dropped
        contents = [m.content for m in trimmed if m.role == "user"]
        assert "new question" in contents

    def test_empty_messages(self) -> None:
        cm = ContextManager(max_input_tokens=1000)
        assert cm.trim([]) == []

    def test_system_only(self) -> None:
        cm = ContextManager(max_input_tokens=1000)
        messages = [ChatMessage(role="system", content="sys")]
        trimmed = cm.trim(messages)
        assert len(trimmed) == 1

    def test_tool_results_grouped_with_assistant(self) -> None:
        """Tool result messages should stay with their assistant message."""
        cm = ContextManager(max_input_tokens=100000)
        messages = [
            ChatMessage(role="system", content="sys"),
            ChatMessage(role="user", content="Q1"),
            ChatMessage(role="assistant", content=None, tool_calls=[]),
            ChatMessage(role="tool", content="result", tool_call_id="tc1"),
            ChatMessage(role="assistant", content="Based on the result..."),
            ChatMessage(role="user", content="Q2"),
            ChatMessage(role="assistant", content="A2"),
        ]
        trimmed = cm.trim(messages)
        assert len(trimmed) == len(messages)

    def test_max_input_tokens_property(self) -> None:
        cm = ContextManager(max_input_tokens=8000)
        assert cm.max_input_tokens == 8000
