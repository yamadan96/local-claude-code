"""grep tool implementation (content search)."""

from __future__ import annotations

import re
from typing import Any

from lcc.tools.base import ToolExecutionContext, ToolResult

DEFAULT_MAX_MATCHES = 50


class GrepTool:
    """Search file contents for a regex or literal pattern."""

    @property
    def name(self) -> str:
        return "grep"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "grep",
                "description": ("Search file contents for a regex or literal pattern."),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Search pattern (regex)",
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "Directory or file to search (default: workspace root)"
                            ),
                        },
                        "file_glob": {
                            "type": "string",
                            "description": (
                                "Only search files matching this glob (e.g. '*.py')"
                            ),
                        },
                        "max_matches": {
                            "type": "integer",
                            "description": (
                                f"Max results to return (default {DEFAULT_MAX_MATCHES})"
                            ),
                            "minimum": 1,
                        },
                    },
                    "required": ["pattern"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        pattern_str = args.get("pattern", "")
        if not pattern_str:
            return ToolResult(
                status="error", output="Missing required argument: pattern"
            )

        try:
            regex = re.compile(pattern_str)
        except re.error as exc:
            return ToolResult(status="error", output=f"Invalid regex pattern: {exc}")

        search_path_str = args.get("path", ".")
        file_glob = args.get("file_glob")
        max_matches = int(args.get("max_matches", DEFAULT_MAX_MATCHES))

        try:
            search_path = ctx.sandbox.validate_path(search_path_str)
        except Exception as exc:
            return ToolResult(status="error", output=str(exc))

        if not search_path.exists():
            return ToolResult(
                status="error", output=f"Path not found: {search_path_str}"
            )

        # Collect files to search
        files_to_search: list[Any] = []
        if search_path.is_file():
            files_to_search = [search_path]
        elif search_path.is_dir():
            if file_glob:
                files_to_search = sorted(search_path.rglob(file_glob))
            else:
                files_to_search = sorted(search_path.rglob("*"))
        else:
            return ToolResult(
                status="error",
                output=f"Not a file or directory: {search_path_str}",
            )

        results: list[str] = []
        root = ctx.sandbox.root

        for fpath in files_to_search:
            if not fpath.is_file():
                continue
            # Skip hidden files
            try:
                rel = fpath.relative_to(root)
                if any(part.startswith(".") for part in rel.parts):
                    continue
            except ValueError:
                continue

            # Skip binary files
            try:
                content = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            for line_num, line in enumerate(content.splitlines(), start=1):
                if regex.search(line):
                    results.append(f"{rel}:{line_num}: {line.rstrip()}")
                    if len(results) >= max_matches:
                        break

            if len(results) >= max_matches:
                break

        if not results:
            return ToolResult(
                status="ok", output=f"No matches for pattern '{pattern_str}'"
            )

        output = "\n".join(results)
        if len(results) >= max_matches:
            output += f"\n[truncated at {max_matches} matches]"

        return ToolResult(status="ok", output=output)
