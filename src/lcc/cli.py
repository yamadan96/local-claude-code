"""CLI entry point: argparse, one-shot mode, and REPL launch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lcc import __version__
from lcc.agent.context import ContextManager
from lcc.agent.loop import AgentRunner
from lcc.agent.messages import ConversationState
from lcc.config.loader import load_config
from lcc.config.models import PermissionMode
from lcc.providers.openai_compat import OpenAICompatProvider
from lcc.safety.permissions import PermissionManager, auto_approve
from lcc.safety.sandbox import WorkspaceSandbox
from lcc.tools.base import ToolExecutionContext
from lcc.tools.registry import ToolRegistry
from lcc.utils.logging import setup_logging


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="lcc",
        description="local-claude-code: A local-first AI coding agent",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"lcc {__version__}",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        type=str,
        default=None,
        help="One-shot mode: run a single prompt and exit",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override model name",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Override API base URL",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Override API key",
    )
    parser.add_argument(
        "--permission-mode",
        type=str,
        choices=["ask", "auto"],
        default=None,
        help="Override permission mode",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Override working directory",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def _register_all_tools(registry: ToolRegistry) -> None:
    """Register all built-in tools."""
    from lcc.tools.fs_edit import EditFileTool
    from lcc.tools.fs_read import ReadFileTool
    from lcc.tools.fs_write import WriteFileTool
    from lcc.tools.glob_search import GlobTool
    from lcc.tools.grep_search import GrepTool
    from lcc.tools.list_dir import ListDirTool
    from lcc.tools.shell import BashTool

    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(BashTool())
    registry.register(GlobTool())
    registry.register(GrepTool())
    registry.register(ListDirTool())


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    setup_logging(verbose=args.verbose)

    # Build CLI overrides dict
    cli_overrides: dict[str, str | None] = {}
    if args.model is not None:
        cli_overrides["model"] = args.model
    if args.base_url is not None:
        cli_overrides["base_url"] = args.base_url
    if args.api_key is not None:
        cli_overrides["api_key"] = args.api_key
    if args.permission_mode is not None:
        cli_overrides["permission_mode"] = args.permission_mode

    # Load config
    config = load_config(
        cli_overrides=cli_overrides,
        cwd=args.cwd,
    )

    # Initialize components
    workspace_root = Path(config.cwd).resolve()
    sandbox = WorkspaceSandbox(workspace_root, allow_outside=config.allow_outside_cwd)

    perm_mode = PermissionMode(config.permission_mode)
    prompt_fn = auto_approve if perm_mode == PermissionMode.AUTO else None
    permissions = PermissionManager(mode=perm_mode, prompt_fn=prompt_fn)

    tool_ctx = ToolExecutionContext(sandbox=sandbox, permissions=permissions)

    registry = ToolRegistry()
    _register_all_tools(registry)

    provider = OpenAICompatProvider(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
    )

    conversation = ConversationState()
    context_mgr = ContextManager(max_input_tokens=config.max_input_tokens)

    runner = AgentRunner(
        provider=provider,
        registry=registry,
        context_manager=context_mgr,
        conversation=conversation,
        tool_context=tool_ctx,
        model=config.model,
        max_tokens=config.max_output_tokens,
    )

    # One-shot mode
    if args.prompt:
        return _run_oneshot(runner, args.prompt)

    # REPL mode
    return _run_repl(config, provider, runner, registry)


def _run_oneshot(runner: AgentRunner, prompt: str) -> int:
    """Run a single prompt and exit."""
    try:
        result = runner.run_turn(prompt)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if result.final_text:
        print(result.final_text)
    return 0


def _run_repl(config, provider, runner, registry) -> int:
    """Launch the interactive REPL."""
    from lcc.repl import ReplSession

    session = ReplSession(
        config=config,
        provider=provider,
        runner=runner,
        registry=registry,
    )
    return session.run()
