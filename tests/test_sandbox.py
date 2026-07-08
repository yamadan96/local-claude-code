"""Tests for workspace sandbox: path resolution and containment."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lcc.safety.sandbox import SandboxViolation, WorkspaceSandbox


class TestWorkspaceSandbox:
    def test_resolve_relative_path(
        self, sandbox: WorkspaceSandbox, tmp_workspace: Path
    ) -> None:
        resolved = sandbox.resolve_path("hello.txt")
        assert resolved == (tmp_workspace / "hello.txt").resolve()

    def test_resolve_nested_relative_path(
        self, sandbox: WorkspaceSandbox, tmp_workspace: Path
    ) -> None:
        resolved = sandbox.resolve_path("subdir/nested.txt")
        assert resolved == (tmp_workspace / "subdir" / "nested.txt").resolve()

    def test_resolve_absolute_path_inside(
        self, sandbox: WorkspaceSandbox, tmp_workspace: Path
    ) -> None:
        abs_path = str(tmp_workspace / "hello.txt")
        resolved = sandbox.resolve_path(abs_path)
        assert resolved == (tmp_workspace / "hello.txt").resolve()

    def test_parent_traversal_blocked(self, sandbox: WorkspaceSandbox) -> None:
        with pytest.raises(SandboxViolation):
            sandbox.validate_path("../../etc/passwd")

    def test_double_parent_traversal_blocked(self, sandbox: WorkspaceSandbox) -> None:
        with pytest.raises(SandboxViolation):
            sandbox.validate_path("subdir/../../..")

    def test_absolute_path_outside_blocked(self, sandbox: WorkspaceSandbox) -> None:
        with pytest.raises(SandboxViolation):
            sandbox.validate_path("/etc/passwd")

    def test_absolute_path_tmp_blocked(self, sandbox: WorkspaceSandbox) -> None:
        with pytest.raises(SandboxViolation):
            sandbox.validate_path("/tmp/evil.txt")

    def test_symlink_escape_blocked(
        self, sandbox: WorkspaceSandbox, tmp_workspace: Path
    ) -> None:
        """A symlink inside workspace pointing outside should be rejected."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"external secret")
            external = Path(f.name)

        try:
            link = tmp_workspace / "escape_link"
            link.symlink_to(external)
            with pytest.raises(SandboxViolation):
                sandbox.validate_path("escape_link")
        finally:
            external.unlink(missing_ok=True)

    def test_allow_outside_flag(self, tmp_workspace: Path) -> None:
        """With allow_outside=True, paths outside workspace are allowed."""
        permissive = WorkspaceSandbox(tmp_workspace, allow_outside=True)
        # Should not raise
        permissive.validate_path("/etc/passwd")

    def test_validate_path_returns_resolved(
        self, sandbox: WorkspaceSandbox, tmp_workspace: Path
    ) -> None:
        result = sandbox.validate_path("hello.txt")
        assert result.is_absolute()
        assert result == (tmp_workspace / "hello.txt").resolve()

    def test_tilde_expansion(self, sandbox: WorkspaceSandbox) -> None:
        """~ should be expanded but if it escapes workspace, it's blocked."""
        # ~ expands to home dir which is outside the temp workspace
        with pytest.raises(SandboxViolation):
            sandbox.validate_path("~/some_file.txt")

    def test_dot_path_resolves_to_root(
        self, sandbox: WorkspaceSandbox, tmp_workspace: Path
    ) -> None:
        resolved = sandbox.resolve_path(".")
        assert resolved == tmp_workspace.resolve()

    def test_root_property(
        self, sandbox: WorkspaceSandbox, tmp_workspace: Path
    ) -> None:
        assert sandbox.root == tmp_workspace.resolve()
