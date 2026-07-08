"""Tests for grep tool."""

from __future__ import annotations

from pathlib import Path

from lcc.tools.base import ToolExecutionContext
from lcc.tools.grep_search import GrepTool


class TestGrepTool:
    def setup_method(self) -> None:
        self.tool = GrepTool()

    def test_name(self) -> None:
        assert self.tool.name == "grep"

    def test_find_pattern_in_file(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "Hello"}, tool_ctx)
        assert result.status == "ok"
        assert "hello.txt" in result.output
        assert "Hello" in result.output

    def test_regex_pattern(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": r"x\s*\+\s*y"}, tool_ctx)
        assert result.status == "ok"
        assert "data.py" in result.output

    def test_no_matches(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "ZZZZZZZ_NO_MATCH"}, tool_ctx)
        assert result.status == "ok"
        assert "No matches" in result.output

    def test_file_glob_filter(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": ".*", "file_glob": "*.py"}, tool_ctx)
        assert result.status == "ok"
        assert "data.py" in result.output
        assert "hello.txt" not in result.output

    def test_search_specific_file(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "Line", "path": "hello.txt"}, tool_ctx)
        assert result.status == "ok"
        assert "Line 2" in result.output

    def test_invalid_regex(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "[invalid"}, tool_ctx)
        assert result.status == "error"
        assert "regex" in result.output.lower() or "Invalid" in result.output

    def test_missing_pattern(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({}, tool_ctx)
        assert result.status == "error"

    def test_sandbox_violation(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"pattern": "root", "path": "/etc"}, tool_ctx)
        assert result.status == "error"

    def test_max_matches_limit(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        (tmp_workspace / "many.txt").write_text(
            "\n".join([f"match_{i}" for i in range(100)])
        )
        result = self.tool.execute({"pattern": "match_", "max_matches": 5}, tool_ctx)
        assert result.status == "ok"
        assert "truncated" in result.output.lower()
