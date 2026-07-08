"""ToolRegistry: lookup, schema export, and dispatch."""

from __future__ import annotations

import json
import logging
from typing import Any

from lcc.agent.recovery import fuzzy_match_tool_name, recover_tool_call_json
from lcc.safety.permissions import PermissionRequest
from lcc.tools.base import Tool, ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of available tools with lookup, schema export, and dispatch."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by its name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Look up a tool by exact name."""
        return self._tools.get(name)

    def names(self) -> list[str]:
        """Return all registered tool names."""
        return list(self._tools.keys())

    def openai_schemas(self) -> list[dict[str, Any]]:
        """Return tool schemas in OpenAI function-calling format."""
        return [tool.schema() for tool in self._tools.values()]

    def execute_tool_call(
        self,
        name: str,
        arguments_json: str,
        ctx: ToolExecutionContext,
    ) -> ToolResult:
        """Dispatch a tool call: parse args, check permissions, execute.

        Handles unknown tool names (with fuzzy matching), JSON parse errors
        (with recovery), and permission denials.
        """
        # Look up tool (with fuzzy matching fallback)
        tool = self.get(name)
        if tool is None:
            matched_name = fuzzy_match_tool_name(name, self.names())
            if matched_name:
                logger.info("Fuzzy-matched tool name '%s' -> '%s'", name, matched_name)
                tool = self.get(matched_name)

        if tool is None:
            available = ", ".join(self.names())
            return ToolResult(
                status="error",
                output=f"Unknown tool: '{name}'. Available tools: {available}",
            )

        # Parse arguments
        args = self._parse_arguments(arguments_json)
        if args is None:
            return ToolResult(
                status="error",
                output=(
                    f"Failed to parse tool arguments for '{tool.name}'. "
                    f"Raw input: {arguments_json[:200]}"
                ),
            )

        # Check permissions
        if ctx.permissions.is_privileged(tool.name):
            summary = _summarize_args(tool.name, args)
            decision = ctx.permissions.require(
                PermissionRequest(
                    tool_name=tool.name,
                    description=f"Execute {tool.name}",
                    arguments_summary=summary,
                )
            )
            if not decision.allowed:
                return ToolResult(
                    status="error",
                    output=f"Permission denied for {tool.name}: {decision.reason}",
                )

        # Execute
        try:
            return tool.execute(args, ctx)
        except Exception as exc:
            logger.exception("Tool '%s' raised an exception", tool.name)
            return ToolResult(status="error", output=f"Tool error: {exc}")

    def _parse_arguments(self, arguments_json: str) -> dict[str, Any] | None:
        """Parse tool arguments JSON, with recovery for malformed input."""
        if not arguments_json or arguments_json.strip() == "":
            return {}

        # Try direct parse first
        try:
            result = json.loads(arguments_json)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Try recovery
        recovered = recover_tool_call_json(arguments_json)
        if recovered is not None:
            return recovered

        return None


def _summarize_args(tool_name: str, args: dict[str, Any]) -> str:
    """Create a short summary of tool arguments for permission prompts."""
    if tool_name == "bash":
        return args.get("command", str(args))[:100]
    if tool_name in ("write_file", "edit_file"):
        path = args.get("path", "?")
        return f"path={path}"
    return json.dumps(args, ensure_ascii=False)[:100]
