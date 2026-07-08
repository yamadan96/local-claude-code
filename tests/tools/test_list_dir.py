"""Tests for list_dir tool."""

from __future__ import annotations

from pathlib import Path

from lcc.tools.base import ToolExecutionContext
from lcc.tools.list_dir import ListDirTool


class TestListDirTool:
    def setup_method(self) -> None:
        self.tool = ListDirTool()

    def test_name(self) -> None:
        assert self.tool.name == "list_dir"

    def test_list_root(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({}, tool_ctx)
        assert result.status == "ok"
        assert "hello.txt" in result.output
        assert "data.py" in result.output
        assert "subdir" in result.output

    def test_list_with_explicit_path(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "subdir"}, tool_ctx)
        assert result.status == "ok"
        assert "nested.txt" in result.output

    def test_list_nonexistent_dir(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "no_such_dir"}, tool_ctx)
        assert result.status == "error"

    def test_list_file_not_dir(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "hello.txt"}, tool_ctx)
        assert result.status == "error"
        assert "Not a directory" in result.output

    def test_recursive_listing(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        result = self.tool.execute({"path": ".", "recursive": True}, tool_ctx)
        assert result.status == "ok"
        assert "nested.txt" in result.output

    def test_sandbox_violation(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "../.."}, tool_ctx)
        assert result.status == "error"

    def test_shows_file_sizes(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({}, tool_ctx)
        assert result.status == "ok"
        # Should contain size info like (14B) or (0.1KB)
        assert "B)" in result.output or "KB)" in result.output

    def test_empty_directory(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        (tmp_workspace / "empty_dir").mkdir()
        result = self.tool.execute({"path": "empty_dir"}, tool_ctx)
        assert result.status == "ok"
        assert "empty" in result.output.lower()
