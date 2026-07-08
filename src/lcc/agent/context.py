"""ContextManager: token-budget trimming for conversation history."""

from __future__ import annotations

import json

from lcc.agent.messages import ChatMessage

# Reserve 20% of the budget for model output
OUTPUT_MARGIN_RATIO = 0.20

# Rough chars-to-tokens ratio
CHARS_PER_TOKEN = 4


class ContextManager:
    """Manages trimming of conversation history to fit token budgets.

    v1 strategy: character-based estimate, drop oldest complete groups
    (user + assistant + tool results as a unit). System messages are
    always kept (pinned).
    """

    def __init__(self, max_input_tokens: int) -> None:
        self._max_input_tokens = max_input_tokens

    @property
    def max_input_tokens(self) -> int:
        return self._max_input_tokens

    def trim(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        """Trim messages to fit within the token budget.

        Always keeps system messages and the newest messages.
        Drops oldest user/assistant/tool groups first.
        """
        budget = int(self._max_input_tokens * (1 - OUTPUT_MARGIN_RATIO))

        if self._estimate_tokens(messages) <= budget:
            return messages

        # Separate system messages from the rest
        system_msgs = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]

        system_cost = self._estimate_tokens(system_msgs)
        remaining_budget = budget - system_cost

        if remaining_budget <= 0:
            return system_msgs

        # Group non-system messages into conversation turns
        groups = self._group_messages(non_system)

        # Keep newest groups first, drop oldest
        kept_groups: list[list[ChatMessage]] = []
        current_cost = 0

        for group in reversed(groups):
            group_cost = self._estimate_tokens(group)
            if current_cost + group_cost <= remaining_budget:
                kept_groups.insert(0, group)
                current_cost += group_cost
            else:
                break

        # Flatten kept groups
        kept_messages = system_msgs
        for group in kept_groups:
            kept_messages.extend(group)

        return kept_messages

    def _estimate_tokens(self, messages: list[ChatMessage]) -> int:
        """Estimate token count using chars / 4 heuristic."""
        total_chars = 0
        for msg in messages:
            total_chars += len(json.dumps(msg.to_api_dict()))
        return total_chars // CHARS_PER_TOKEN

    def _group_messages(self, messages: list[ChatMessage]) -> list[list[ChatMessage]]:
        """Group messages into logical conversation turns.

        A group starts with a user message and includes subsequent
        assistant and tool messages until the next user message.
        """
        if not messages:
            return []

        groups: list[list[ChatMessage]] = []
        current_group: list[ChatMessage] = []

        for msg in messages:
            if msg.role == "user" and current_group:
                groups.append(current_group)
                current_group = []
            current_group.append(msg)

        if current_group:
            groups.append(current_group)

        return groups
