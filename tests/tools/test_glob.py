"""Tests for glob tool."""

from __future__ import annotations

from pathlib import Path

from lcc.tools.base import ToolExecutionContext
from lcc.tools.glob_search import GlobTool


class TestGlobTool:
    def setup_method(self) -> None:
        self.tool = GlobTool()

    def test_name(self) -> None:
        assert self.tool.name == "glob"

    def test_find_txt_files(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "**/*.txt"}, tool_ctx)
        assert result.status == "ok"
        assert "hello.txt" in result.output
        assert "nested.txt" in result.output

    def test_find_py_files(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "*.py"}, tool_ctx)
        assert result.status == "ok"
        assert "data.py" in result.output

    def test_no_matches(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "*.xyz"}, tool_ctx)
        assert result.status == "ok"
        assert "No files matching" in result.output

    def test_missing_pattern(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({}, tool_ctx)
        assert result.status == "error"

    def test_hidden_files_excluded_by_default(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        (tmp_workspace / ".hidden_file.txt").write_text("secret")
        result = self.tool.execute({"pattern": "**/*.txt"}, tool_ctx)
        assert ".hidden_file.txt" not in result.output

    def test_hidden_files_included(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        (tmp_workspace / ".visible.txt").write_text("found me")
        result = self.tool.execute(
            {"pattern": "**/*.txt", "include_hidden": True}, tool_ctx
        )
        assert ".visible.txt" in result.output
