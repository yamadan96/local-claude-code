"""Tests for permission management."""

from __future__ import annotations

from lcc.safety.permissions import (
    PermissionDecision,
    PermissionManager,
    PermissionMode,
    PermissionRequest,
    auto_approve,
    auto_deny,
)


class TestPermissionManager:
    def test_auto_mode_always_allows(self) -> None:
        pm = PermissionManager(mode=PermissionMode.AUTO)
        action = PermissionRequest(tool_name="bash", description="run command")
        decision = pm.require(action)
        assert decision.allowed

    def test_ask_mode_allows_read_only_tools(self) -> None:
        pm = PermissionManager(mode=PermissionMode.ASK, prompt_fn=auto_deny)
        action = PermissionRequest(tool_name="read_file", description="read a file")
        decision = pm.require(action)
        assert decision.allowed

    def test_ask_mode_denies_privileged_tools_when_user_denies(self) -> None:
        pm = PermissionManager(mode=PermissionMode.ASK, prompt_fn=auto_deny)
        action = PermissionRequest(tool_name="bash", description="rm -rf /")
        decision = pm.require(action)
        assert not decision.allowed

    def test_ask_mode_allows_privileged_tools_when_user_approves(self) -> None:
        pm = PermissionManager(mode=PermissionMode.ASK, prompt_fn=auto_approve)
        action = PermissionRequest(tool_name="write_file", description="write file")
        decision = pm.require(action)
        assert decision.allowed

    def test_is_privileged_bash(self) -> None:
        pm = PermissionManager()
        assert pm.is_privileged("bash")

    def test_is_privileged_write_file(self) -> None:
        pm = PermissionManager()
        assert pm.is_privileged("write_file")

    def test_is_privileged_edit_file(self) -> None:
        pm = PermissionManager()
        assert pm.is_privileged("edit_file")

    def test_is_not_privileged_read_file(self) -> None:
        pm = PermissionManager()
        assert not pm.is_privileged("read_file")

    def test_is_not_privileged_glob(self) -> None:
        pm = PermissionManager()
        assert not pm.is_privileged("glob")

    def test_mode_property(self) -> None:
        pm = PermissionManager(mode=PermissionMode.ASK)
        assert pm.mode == PermissionMode.ASK
        pm.mode = PermissionMode.AUTO
        assert pm.mode == PermissionMode.AUTO

    def test_auto_approve_helper(self) -> None:
        action = PermissionRequest(tool_name="bash", description="test")
        result = auto_approve(action)
        assert result.allowed

    def test_auto_deny_helper(self) -> None:
        action = PermissionRequest(tool_name="bash", description="test")
        result = auto_deny(action)
        assert not result.allowed

    def test_permission_decision_dataclass(self) -> None:
        d = PermissionDecision(allowed=True, reason="test reason")
        assert d.allowed
        assert d.reason == "test reason"
