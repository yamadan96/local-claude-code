"""read_file tool implementation."""

from __future__ import annotations

from typing import Any

from lcc.tools.base import ToolExecutionContext, ToolResult

MAX_FILE_SIZE_BYTES = 1_000_000  # 1 MB


class ReadFileTool:
    """Read the contents of a file with optional line range."""

    @property
    def name(self) -> str:
        return "read_file"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": (
                    "Read the contents of a file. "
                    "Returns the file content with line numbers."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path (relative to workspace root)",
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Start line (1-indexed, optional)",
                            "minimum": 1,
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "End line (1-indexed, optional)",
                            "minimum": 1,
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        path_str = args.get("path", "")
        if not path_str:
            return ToolResult(status="error", output="Missing required argument: path")

        try:
            resolved = ctx.sandbox.validate_path(path_str)
        except Exception as exc:
            return ToolResult(status="error", output=str(exc))

        if not resolved.exists():
            return ToolResult(status="error", output=f"File not found: {path_str}")
        if not resolved.is_file():
            return ToolResult(status="error", output=f"Not a file: {path_str}")

        # Size check
        file_size = resolved.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            return ToolResult(
                status="error",
                output=(
                    f"File too large: {file_size} bytes "
                    f"(max {MAX_FILE_SIZE_BYTES} bytes). "
                    f"Use start_line/end_line to read a portion."
                ),
            )

        # Binary check
        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult(
                status="error",
                output=f"Cannot read binary file: {path_str}",
            )

        lines = content.splitlines(keepends=True)
        start = args.get("start_line")
        end = args.get("end_line")

        if start is not None:
            start = max(1, int(start))
        else:
            start = 1

        if end is not None:
            end = min(len(lines), int(end))
        else:
            end = len(lines)

        selected = lines[start - 1 : end]
        numbered = "".join(f"{start + i}\t{line}" for i, line in enumerate(selected))

        return ToolResult(status="ok", output=numbered)
