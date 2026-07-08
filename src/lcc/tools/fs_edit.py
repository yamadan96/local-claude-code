"""edit_file tool implementation (exact string replace)."""

from __future__ import annotations

from typing import Any

from lcc.tools.base import ToolExecutionContext, ToolResult


class EditFileTool:
    """Replace exact text in a file."""

    @property
    def name(self) -> str:
        return "edit_file"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": (
                    "Replace exact text in a file. old_text must match "
                    "exactly once unless replace_all is true."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path (relative to workspace root)",
                        },
                        "old_text": {
                            "type": "string",
                            "description": "Exact text to find and replace",
                        },
                        "new_text": {
                            "type": "string",
                            "description": "Replacement text",
                        },
                        "replace_all": {
                            "type": "boolean",
                            "description": ("Replace all occurrences (default false)"),
                            "default": False,
                        },
                    },
                    "required": ["path", "old_text", "new_text"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        path_str = args.get("path", "")
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        replace_all = args.get("replace_all", False)

        if not path_str:
            return ToolResult(status="error", output="Missing required argument: path")
        if not old_text:
            return ToolResult(
                status="error", output="Missing required argument: old_text"
            )

        try:
            resolved = ctx.sandbox.validate_path(path_str)
        except Exception as exc:
            return ToolResult(status="error", output=str(exc))

        if not resolved.exists():
            return ToolResult(status="error", output=f"File not found: {path_str}")
        if not resolved.is_file():
            return ToolResult(status="error", output=f"Not a file: {path_str}")

        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult(
                status="error", output=f"Cannot read binary file: {path_str}"
            )

        match_count = content.count(old_text)
        if match_count == 0:
            return ToolResult(
                status="error",
                output=(
                    f"Found 0 matches for old_text in {path_str}. "
                    f"Use read_file first to see exact content."
                ),
            )

        if not replace_all and match_count > 1:
            return ToolResult(
                status="error",
                output=(
                    f"Found {match_count} matches for old_text in {path_str}. "
                    f"Expected exactly 1. Use replace_all=true to replace all, "
                    f"or provide more context to make old_text unique."
                ),
            )

        if replace_all:
            new_content = content.replace(old_text, new_text)
        else:
            new_content = content.replace(old_text, new_text, 1)

        try:
            resolved.write_text(new_content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(status="error", output=f"Write failed: {exc}")

        return ToolResult(
            status="ok",
            output=(f"Replaced {match_count} occurrence(s) in {path_str}"),
        )
