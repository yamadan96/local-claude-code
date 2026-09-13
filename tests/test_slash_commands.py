"""Tests for REPL slash commands applying changes to the running session."""

from __future__ import annotations

from pathlib import Path

from lcc.agent.context import ContextManager
from lcc.agent.loop import AgentRunner
from lcc.agent.messages import ConversationState
from lcc.config.models import AppConfig
from lcc.providers.openai_compat import OpenAICompatProvider
from lcc.safety.permissions import (
    PermissionManager,
    PermissionMode,
    PermissionRequest,
    auto_deny,
)
from lcc.safety.sandbox import WorkspaceSandbox
from lcc.slash_commands import SlashCommandDispatcher
from lcc.tools.base import ToolExecutionContext
from lcc.tools.registry import ToolRegistry


def _make_session(
    tmp_path: Path, mode: PermissionMode = PermissionMode.ASK
) -> tuple[AppConfig, OpenAICompatProvider, AgentRunner, PermissionManager]:
    config = AppConfig(
        model="model-a", base_url="http://host-a:1/v1", permission_mode=mode
    )
    provider = OpenAICompatProvider(base_url=config.base_url, model=config.model)
    permissions = PermissionManager(mode=mode, prompt_fn=auto_deny)
    runner = AgentRunner(
        provider=provider,
        registry=ToolRegistry(),
        context_manager=ContextManager(max_input_tokens=1000),
        conversation=ConversationState(),
        tool_context=ToolExecutionContext(
            sandbox=WorkspaceSandbox(tmp_path), permissions=permissions
        ),
        model=config.model,
    )
    return config, provider, runner, permissions


def _dispatcher(
    config: AppConfig,
    provider: OpenAICompatProvider,
    runner: AgentRunner,
    permissions: PermissionManager,
) -> SlashCommandDispatcher:
    return SlashCommandDispatcher(
        config=config, runner=runner, provider=provider, permissions=permissions
    )


class TestSlashCommandsApplyAtRuntime:
    def test_model_switch_updates_runner_and_provider(self, tmp_path: Path) -> None:
        config, provider, runner, permissions = _make_session(tmp_path)
        _dispatcher(config, provider, runner, permissions).dispatch("/model model-b")
        assert config.model == "model-b"
        assert runner.model == "model-b"
        assert provider.model == "model-b"

    def test_base_url_switch_updates_provider(self, tmp_path: Path) -> None:
        config, provider, runner, permissions = _make_session(tmp_path)
        _dispatcher(config, provider, runner, permissions).dispatch(
            "/base_url http://host-b:2/v1/"
        )
        assert config.base_url == "http://host-b:2/v1/"
        assert provider.base_url == "http://host-b:2/v1"

    def test_permission_switch_to_ask_enforces_prompt(self, tmp_path: Path) -> None:
        """Switching auto -> ask must make privileged tools go through the prompt."""
        config, provider, runner, permissions = _make_session(
            tmp_path, mode=PermissionMode.AUTO
        )
        bash = PermissionRequest(tool_name="bash", description="run")
        assert permissions.require(bash).allowed

        _dispatcher(config, provider, runner, permissions).dispatch("/permission ask")

        assert config.permission_mode == PermissionMode.ASK
        assert permissions.mode == PermissionMode.ASK
        assert not permissions.require(bash).allowed

    def test_permission_switch_to_auto_skips_prompt(self, tmp_path: Path) -> None:
        config, provider, runner, permissions = _make_session(tmp_path)
        _dispatcher(config, provider, runner, permissions).dispatch("/permission auto")
        assert permissions.mode == PermissionMode.AUTO
        bash = PermissionRequest(tool_name="bash", description="run")
        assert permissions.require(bash).allowed

    def test_invalid_permission_mode_changes_nothing(self, tmp_path: Path) -> None:
        config, provider, runner, permissions = _make_session(tmp_path)
        result = _dispatcher(config, provider, runner, permissions).dispatch(
            "/permission sometimes"
        )
        assert "Invalid permission mode" in result.output
        assert config.permission_mode == PermissionMode.ASK
        assert permissions.mode == PermissionMode.ASK

    def test_dispatcher_without_runtime_objects_still_updates_config(self) -> None:
        config = AppConfig()
        dispatcher = SlashCommandDispatcher(config=config)
        dispatcher.dispatch("/model other")
        dispatcher.dispatch("/permission auto")
        assert config.model == "other"
        assert config.permission_mode == PermissionMode.AUTO
