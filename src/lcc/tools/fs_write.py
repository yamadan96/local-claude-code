"""write_file tool implementation."""

from __future__ import annotations

from typing import Any

from lcc.tools.base import ToolExecutionContext, ToolResult


class WriteFileTool:
    """Write content to a file. Creates the file if it doesn't exist."""

    @property
    def name(self) -> str:
        return "write_file"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": (
                    "Write content to a file. Creates the file if it doesn't "
                    "exist, overwrites if it does."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path (relative to workspace root)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write",
                        },
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        path_str = args.get("path", "")
        content = args.get("content")

        if not path_str:
            return ToolResult(status="error", output="Missing required argument: path")
        if content is None:
            return ToolResult(
                status="error", output="Missing required argument: content"
            )

        try:
            resolved = ctx.sandbox.validate_path(path_str)
        except Exception as exc:
            return ToolResult(status="error", output=str(exc))

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(status="error", output=f"Write failed: {exc}")

        return ToolResult(
            status="ok", output=f"Wrote {len(content)} chars to {path_str}"
        )
