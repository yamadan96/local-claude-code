"""glob tool implementation (file pattern search)."""

from __future__ import annotations

from typing import Any

from lcc.tools.base import ToolExecutionContext, ToolResult

MAX_RESULTS = 1000


class GlobTool:
    """Find files matching a glob pattern within the workspace."""

    @property
    def name(self) -> str:
        return "glob"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "glob",
                "description": (
                    "Find files matching a glob pattern within the workspace."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g. '**/*.py')",
                        },
                        "include_hidden": {
                            "type": "boolean",
                            "description": ("Include hidden files (default false)"),
                            "default": False,
                        },
                    },
                    "required": ["pattern"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        pattern = args.get("pattern", "")
        if not pattern:
            return ToolResult(
                status="error", output="Missing required argument: pattern"
            )

        include_hidden = args.get("include_hidden", False)
        root = ctx.sandbox.root

        try:
            matches = sorted(root.glob(pattern))
        except ValueError as exc:
            return ToolResult(status="error", output=f"Invalid glob pattern: {exc}")

        # Filter hidden files if requested
        if not include_hidden:
            matches = [
                m
                for m in matches
                if not any(part.startswith(".") for part in m.relative_to(root).parts)
            ]

        # Filter to workspace-contained paths only
        valid_matches: list[str] = []
        for match in matches:
            try:
                resolved = match.resolve()
                resolved.relative_to(ctx.sandbox.root)
                valid_matches.append(str(match.relative_to(root)))
            except (ValueError, OSError):
                continue

        if len(valid_matches) > MAX_RESULTS:
            truncated = valid_matches[:MAX_RESULTS]
            output = "\n".join(truncated)
            output += (
                f"\n[truncated: showing {MAX_RESULTS} of {len(valid_matches)} matches]"
            )
            return ToolResult(status="ok", output=output)

        if not valid_matches:
            return ToolResult(status="ok", output=f"No files matching '{pattern}'")

        return ToolResult(status="ok", output="\n".join(valid_matches))
