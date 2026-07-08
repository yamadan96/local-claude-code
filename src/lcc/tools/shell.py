"""bash tool implementation (subprocess execution)."""

from __future__ import annotations

import subprocess
from typing import Any

from lcc.tools.base import ToolExecutionContext, ToolResult

MAX_OUTPUT_BYTES = 100_000  # 100 KB
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300


class BashTool:
    """Execute a shell command and return stdout/stderr."""

    @property
    def name(self) -> str:
        return "bash"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "bash",
                "description": ("Execute a shell command and return stdout/stderr."),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": (
                                f"Timeout in seconds "
                                f"(default {DEFAULT_TIMEOUT_SECONDS})"
                            ),
                            "minimum": 1,
                            "maximum": MAX_TIMEOUT_SECONDS,
                        },
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        command = args.get("command", "")
        if not command:
            return ToolResult(
                status="error", output="Missing required argument: command"
            )

        timeout = min(
            int(args.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
            MAX_TIMEOUT_SECONDS,
        )

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(ctx.sandbox.root),
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                status="error",
                output=f"Command timed out after {timeout} seconds",
            )
        except OSError as exc:
            return ToolResult(status="error", output=f"Command failed: {exc}")

        output_parts: list[str] = []
        if result.stdout:
            stdout = _truncate(result.stdout, MAX_OUTPUT_BYTES)
            output_parts.append(stdout)
        if result.stderr:
            stderr = _truncate(result.stderr, MAX_OUTPUT_BYTES)
            output_parts.append(f"[stderr]\n{stderr}")

        output = "\n".join(output_parts) if output_parts else "(no output)"

        if result.returncode != 0:
            output = f"[exit code {result.returncode}]\n{output}"
            return ToolResult(status="error", output=output)

        return ToolResult(status="ok", output=output)


def _truncate(text: str, max_bytes: int) -> str:
    """Truncate text to max_bytes, adding a truncation notice if needed."""
    if len(text.encode("utf-8", errors="replace")) <= max_bytes:
        return text
    truncated = text.encode("utf-8", errors="replace")[:max_bytes].decode(
        "utf-8", errors="replace"
    )
    return f"{truncated}\n[truncated, output exceeded {max_bytes} bytes]"
