"""Workspace sandbox: path resolution and containment enforcement."""

from __future__ import annotations

from pathlib import Path


class SandboxViolation(Exception):
    """Raised when a path escapes the workspace sandbox."""


class WorkspaceSandbox:
    """Enforces that all file operations stay within the workspace root.

    Resolves symlinks and normalizes paths before containment checks.
    """

    def __init__(self, workspace_root: Path, *, allow_outside: bool = False) -> None:
        self._root = workspace_root.resolve()
        self._allow_outside = allow_outside

    @property
    def root(self) -> Path:
        """Return the resolved workspace root."""
        return self._root

    def resolve_path(self, path: str) -> Path:
        """Resolve a user-supplied path to an absolute, canonical path.

        - Expands ~ (home dir)
        - Resolves relative paths against workspace root
        - Resolves symlinks
        """
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self._root / p
        return p.resolve()

    def ensure_within_workspace(self, path: Path) -> None:
        """Raise SandboxViolation if the resolved path escapes the workspace.

        The path must already be resolved (via resolve_path or Path.resolve()).
        """
        if self._allow_outside:
            return

        resolved = path.resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise SandboxViolation(
                f"Path '{resolved}' is outside the workspace root '{self._root}'. "
                f"Access denied."
            ) from exc

    def validate_path(self, path: str) -> Path:
        """Resolve and validate a path in one step. Returns the resolved path."""
        resolved = self.resolve_path(path)
        self.ensure_within_workspace(resolved)
        return resolved
