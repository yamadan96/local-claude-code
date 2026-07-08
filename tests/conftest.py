"""Shared test fixtures: mock provider, temp workspace, tool context."""

from __future__ import annotations

from pathlib import Path

import pytest

from lcc.agent.messages import ConversationState
from lcc.safety.permissions import (
    PermissionManager,
    PermissionMode,
    auto_approve,
    auto_deny,
)
from lcc.safety.sandbox import WorkspaceSandbox
from lcc.tools.base import ToolExecutionContext


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory with sample files."""
    # Create sample files
    (tmp_path / "hello.txt").write_text("Hello, World!\nLine 2\nLine 3\n")
    (tmp_path / "data.py").write_text("x = 1\ny = 2\nresult = x + y\nprint(result)\n")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("nested content\n")
    return tmp_path


@pytest.fixture
def sandbox(tmp_workspace: Path) -> WorkspaceSandbox:
    """Create a WorkspaceSandbox for the temp workspace."""
    return WorkspaceSandbox(tmp_workspace)


@pytest.fixture
def sandbox_allow_outside(tmp_workspace: Path) -> WorkspaceSandbox:
    """Create a sandbox that allows outside access."""
    return WorkspaceSandbox(tmp_workspace, allow_outside=True)


@pytest.fixture
def permissions_auto() -> PermissionManager:
    """Create a PermissionManager in auto mode."""
    return PermissionManager(mode=PermissionMode.AUTO, prompt_fn=auto_approve)


@pytest.fixture
def permissions_deny() -> PermissionManager:
    """Create a PermissionManager that always denies."""
    return PermissionManager(mode=PermissionMode.ASK, prompt_fn=auto_deny)


@pytest.fixture
def tool_ctx(
    sandbox: WorkspaceSandbox, permissions_auto: PermissionManager
) -> ToolExecutionContext:
    """Create a ToolExecutionContext with auto-approve permissions."""
    return ToolExecutionContext(sandbox=sandbox, permissions=permissions_auto)


@pytest.fixture
def tool_ctx_deny(
    sandbox: WorkspaceSandbox, permissions_deny: PermissionManager
) -> ToolExecutionContext:
    """Create a ToolExecutionContext that denies privileged operations."""
    return ToolExecutionContext(sandbox=sandbox, permissions=permissions_deny)


@pytest.fixture
def conversation() -> ConversationState:
    """Create an empty ConversationState."""
    return ConversationState()
