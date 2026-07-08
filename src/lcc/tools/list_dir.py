"""list_dir tool implementation."""

from __future__ import annotations

from typing import Any

from lcc.tools.base import ToolExecutionContext, ToolResult

MAX_ENTRIES = 500
MAX_RECURSIVE_DEPTH = 3


class ListDirTool:
    """List directory contents with file types and sizes."""

    @property
    def name(self) -> str:
        return "list_dir"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": ("List directory contents with file types and sizes."),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": ("Directory path (default: workspace root)"),
                            "default": ".",
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": ("List recursively (default false)"),
                            "default": False,
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: dict[str, Any], ctx: ToolExecutionContext) -> ToolResult:
        path_str = args.get("path", ".")
        recursive = args.get("recursive", False)

        try:
            resolved = ctx.sandbox.validate_path(path_str)
        except Exception as exc:
            return ToolResult(status="error", output=str(exc))

        if not resolved.exists():
            return ToolResult(status="error", output=f"Directory not found: {path_str}")
        if not resolved.is_dir():
            return ToolResult(status="error", output=f"Not a directory: {path_str}")

        entries: list[str] = []
        root = ctx.sandbox.root

        if recursive:
            self._list_recursive(resolved, root, entries, depth=0)
        else:
            self._list_flat(resolved, root, entries)

        if not entries:
            return ToolResult(status="ok", output="(empty directory)")

        output = "\n".join(entries)
        if len(entries) >= MAX_ENTRIES:
            output += f"\n[truncated at {MAX_ENTRIES} entries]"
        return ToolResult(status="ok", output=output)

    def _list_flat(
        self,
        directory: Any,
        root: Any,
        entries: list[str],
    ) -> None:
        """List a single directory level."""
        try:
            children = sorted(directory.iterdir())
        except PermissionError:
            entries.append("(permission denied)")
            return

        for child in children:
            if len(entries) >= MAX_ENTRIES:
                return
            try:
                rel = child.relative_to(root)
            except ValueError:
                continue
            entry_type = "dir" if child.is_dir() else "file"
            size_info = ""
            if child.is_file():
                try:
                    size = child.stat().st_size
                    size_info = f" ({_human_size(size)})"
                except OSError:
                    pass
            entries.append(f"  {entry_type}  {rel}{size_info}")

    def _list_recursive(
        self,
        directory: Any,
        root: Any,
        entries: list[str],
        depth: int,
    ) -> None:
        """List directory contents recursively up to MAX_RECURSIVE_DEPTH."""
        if depth > MAX_RECURSIVE_DEPTH:
            return
        if len(entries) >= MAX_ENTRIES:
            return

        try:
            children = sorted(directory.iterdir())
        except PermissionError:
            return

        for child in children:
            if len(entries) >= MAX_ENTRIES:
                return
            # Skip hidden entries
            if child.name.startswith("."):
                continue
            try:
                rel = child.relative_to(root)
            except ValueError:
                continue

            if child.is_dir():
                entries.append(f"  dir   {rel}/")
                self._list_recursive(child, root, entries, depth + 1)
            elif child.is_file():
                try:
                    size = child.stat().st_size
                    size_info = f" ({_human_size(size)})"
                except OSError:
                    size_info = ""
                entries.append(f"  file  {rel}{size_info}")


def _human_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    return f"{size_bytes / (1024 * 1024):.1f}MB"
