"""Interactive REPL session."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from lcc import __version__
from lcc.agent.loop import AgentRunner
from lcc.config.models import AppConfig
from lcc.slash_commands import SlashCommandDispatcher
from lcc.tools.registry import ToolRegistry


class ReplSession:
    """Interactive REPL loop for conversing with the agent."""

    def __init__(
        self,
        config: AppConfig,
        provider: Any,
        runner: AgentRunner,
        registry: ToolRegistry,
    ) -> None:
        self._config = config
        self._provider = provider
        self._runner = runner
        self._registry = registry
        self._console = Console()
        self._slash = SlashCommandDispatcher(
            config=config, runner=runner, registry=registry
        )

    def run(self) -> int:
        """Run the REPL loop. Returns exit code."""
        self._print_banner()

        while True:
            try:
                user_input = self._read_input()
            except EOFError:
                self._console.print("\nGoodbye!")
                return 0
            except KeyboardInterrupt:
                self._console.print("\nPress Ctrl+D or type /exit to quit.")
                continue

            if not user_input.strip():
                continue

            # Check for slash command
            cmd_result = self._slash.dispatch(user_input)
            if cmd_result is not None:
                self._console.print(cmd_result.output)
                if cmd_result.should_exit:
                    return 0
                continue

            # Run agent turn
            try:
                result = self._runner.run_turn(user_input)
            except KeyboardInterrupt:
                self._console.print("\n[yellow]Cancelled.[/yellow]")
                continue
            except Exception as exc:
                self._console.print(f"[red]Error: {exc}[/red]")
                continue

            # Render result
            if result.final_text:
                try:
                    self._console.print(Markdown(result.final_text))
                except Exception:
                    self._console.print(result.final_text)

            if result.stopped_reason and result.stopped_reason not in ("natural",):
                self._console.print(f"[yellow]({result.stopped_reason})[/yellow]")

    def _print_banner(self) -> None:
        """Print the startup banner."""
        self._console.print(
            f"[bold]lcc v{__version__}[/bold] | "
            f"model: {self._config.model} | "
            f"{self._config.base_url} | "
            f"mode: {self._config.permission_mode}"
        )
        self._console.print("Type /help for commands, /exit to quit.\n")

    def _read_input(self) -> str:
        """Read user input, supporting multiline via trailing backslash."""
        lines: list[str] = []
        prompt = "[bold green]>[/bold green] "
        first = True

        while True:
            if first:
                self._console.print(prompt, end="")
                first = False
            else:
                self._console.print("  ", end="")

            line = input()
            if line.endswith("\\"):
                lines.append(line[:-1])
            else:
                lines.append(line)
                break

        return "\n".join(lines)
