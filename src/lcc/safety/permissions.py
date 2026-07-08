"""Permission management for tool execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PermissionMode(StrEnum):
    """Permission modes for tool execution."""

    ASK = "ask"
    AUTO = "auto"


@dataclass
class PermissionRequest:
    """A request for permission to execute an action."""

    tool_name: str
    description: str
    arguments_summary: str = ""


@dataclass
class PermissionDecision:
    """The result of a permission check."""

    allowed: bool
    reason: str = ""


# Tools that always require permission in ask mode
PRIVILEGED_TOOLS: set[str] = {"write_file", "edit_file", "bash"}


class PermissionManager:
    """Manages permission checks for tool execution.

    In 'auto' mode, all actions are allowed.
    In 'ask' mode, privileged tools require user confirmation.
    """

    def __init__(
        self,
        mode: PermissionMode = PermissionMode.ASK,
        prompt_fn: PromptFunction | None = None,
    ) -> None:
        self._mode = mode
        self._prompt_fn = prompt_fn or _default_prompt

    @property
    def mode(self) -> PermissionMode:
        """Current permission mode."""
        return self._mode

    @mode.setter
    def mode(self, value: PermissionMode) -> None:
        """Set the permission mode."""
        self._mode = value

    def require(self, action: PermissionRequest) -> PermissionDecision:
        """Check if the action is permitted.

        Returns a PermissionDecision with allowed=True/False.
        """
        if self._mode == PermissionMode.AUTO:
            return PermissionDecision(allowed=True, reason="auto mode")

        if action.tool_name not in PRIVILEGED_TOOLS:
            return PermissionDecision(
                allowed=True, reason="read-only tool, no permission needed"
            )

        return self._prompt_fn(action)

    def is_privileged(self, tool_name: str) -> bool:
        """Check if a tool requires permission in ask mode."""
        return tool_name in PRIVILEGED_TOOLS


# Type alias for prompt function
PromptFunction = type[None]  # placeholder; actual type below


def _default_prompt(action: PermissionRequest) -> PermissionDecision:
    """Default interactive prompt that asks the user for confirmation."""
    summary = action.arguments_summary or action.description
    prompt_text = f"[permission] {action.tool_name}: {summary}\n  Allow? [y/N]: "
    try:
        response = input(prompt_text).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return PermissionDecision(allowed=False, reason="user cancelled")

    if response in ("y", "yes"):
        return PermissionDecision(allowed=True, reason="user approved")
    return PermissionDecision(allowed=False, reason="user denied")


def auto_approve(action: PermissionRequest) -> PermissionDecision:
    """Always approve -- useful for testing."""
    return PermissionDecision(allowed=True, reason="auto-approved for testing")


def auto_deny(action: PermissionRequest) -> PermissionDecision:
    """Always deny -- useful for testing."""
    return PermissionDecision(allowed=False, reason="auto-denied for testing")
