"""Slash commands for the REPL: /help, /clear, /model, /exit, etc."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SlashCommandResult:
    """Result of executing a slash command."""

    output: str
    should_exit: bool = False


class SlashCommandDispatcher:
    """Dispatch table for REPL slash commands."""

    def __init__(
        self,
        config: Any,
        runner: Any = None,
        registry: Any = None,
    ) -> None:
        self._config = config
        self._runner = runner
        self._registry = registry
        self._commands: dict[str, str] = {
            "/help": "Show available commands",
            "/clear": "Reset conversation history",
            "/model": "Show or switch current model (/model [name])",
            "/base_url": "Show or switch endpoint URL (/base_url [url])",
            "/permission": "Show or switch permission mode (/permission [ask|auto])",
            "/tools": "List registered tools with descriptions",
            "/exit": "Exit the REPL",
        }

    def dispatch(self, line: str) -> SlashCommandResult | None:
        """Parse and execute a slash command. Returns None if not a command."""
        stripped = line.strip()
        if not stripped.startswith("/"):
            return None

        parts = stripped.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            return self._cmd_help()
        if cmd == "/clear":
            return self._cmd_clear()
        if cmd == "/model":
            return self._cmd_model(arg)
        if cmd == "/base_url":
            return self._cmd_base_url(arg)
        if cmd == "/permission":
            return self._cmd_permission(arg)
        if cmd == "/tools":
            return self._cmd_tools()
        if cmd in ("/exit", "/quit"):
            return SlashCommandResult(output="Goodbye!", should_exit=True)

        return SlashCommandResult(
            output=f"Unknown command: {cmd}. Type /help for available commands."
        )

    def _cmd_help(self) -> SlashCommandResult:
        lines = ["Available commands:"]
        for cmd, desc in self._commands.items():
            lines.append(f"  {cmd:20s} {desc}")
        return SlashCommandResult(output="\n".join(lines))

    def _cmd_clear(self) -> SlashCommandResult:
        if self._runner:
            self._runner.conversation.clear()
        return SlashCommandResult(output="Conversation history cleared.")

    def _cmd_model(self, arg: str) -> SlashCommandResult:
        if not arg:
            return SlashCommandResult(output=f"Current model: {self._config.model}")
        self._config.model = arg
        return SlashCommandResult(output=f"Model switched to: {arg}")

    def _cmd_base_url(self, arg: str) -> SlashCommandResult:
        if not arg:
            return SlashCommandResult(
                output=f"Current base URL: {self._config.base_url}"
            )
        self._config.base_url = arg
        return SlashCommandResult(output=f"Base URL switched to: {arg}")

    def _cmd_permission(self, arg: str) -> SlashCommandResult:
        if not arg:
            return SlashCommandResult(
                output=f"Current permission mode: {self._config.permission_mode}"
            )
        from lcc.config.models import PermissionMode

        try:
            mode = PermissionMode(arg.lower())
            self._config.permission_mode = mode
            return SlashCommandResult(
                output=f"Permission mode switched to: {mode.value}"
            )
        except ValueError:
            return SlashCommandResult(
                output=f"Invalid permission mode: {arg}. Use 'ask' or 'auto'."
            )

    def _cmd_tools(self) -> SlashCommandResult:
        if not self._registry:
            return SlashCommandResult(output="No tools registered.")
        schemas = self._registry.openai_schemas()
        if not schemas:
            return SlashCommandResult(output="No tools registered.")
        lines = ["Registered tools:"]
        for schema in schemas:
            func = schema.get("function", {})
            name = func.get("name", "?")
            desc = func.get("description", "")
            lines.append(f"  {name:20s} {desc}")
        return SlashCommandResult(output="\n".join(lines))
