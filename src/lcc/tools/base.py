"""Tool protocol, ToolSpec, ToolResult, and ToolExecutionContext."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from lcc.safety.permissions import PermissionManager
from lcc.safety.sandbox import WorkspaceSandbox


@dataclass
class ToolResult:
    """Result of a tool execution."""

    status: Literal["ok", "error"]
    output: str


@dataclass
class ToolExecutionContext:
    """Context passed to every tool execution."""

    sandbox: WorkspaceSandbox
    permissions: PermissionManager


class Tool(Protocol):
    """Protocol that all tools must implement."""

    @property
    def name(self) -> str:
        """Unique name for this tool."""
        ...

    def schema(self) -> dict[str, Any]:
        """Return the OpenAI function-calling JSON schema for this tool."""
        ...

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        """Execute the tool with the given arguments and context."""
        ...
