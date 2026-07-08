"""Tests for edit_file tool."""

from __future__ import annotations

from pathlib import Path

from lcc.tools.base import ToolExecutionContext
from lcc.tools.fs_edit import EditFileTool


class TestEditFileTool:
    def setup_method(self) -> None:
        self.tool = EditFileTool()

    def test_name(self) -> None:
        assert self.tool.name == "edit_file"

    def test_replace_single_occurrence(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        result = self.tool.execute(
            {"path": "hello.txt", "old_text": "Hello, World!", "new_text": "Hi there!"},
            tool_ctx,
        )
        assert result.status == "ok"
        content = (tmp_workspace / "hello.txt").read_text()
        assert "Hi there!" in content
        assert "Hello, World!" not in content

    def test_no_match_found(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute(
            {
                "path": "hello.txt",
                "old_text": "DOES NOT EXIST",
                "new_text": "replacement",
            },
            tool_ctx,
        )
        assert result.status == "error"
        assert "0 matches" in result.output

    def test_multiple_matches_without_replace_all(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        (tmp_workspace / "dupes.txt").write_text("aaa bbb aaa ccc aaa")
        result = self.tool.execute(
            {"path": "dupes.txt", "old_text": "aaa", "new_text": "xxx"},
            tool_ctx,
        )
        assert result.status == "error"
        assert "3 matches" in result.output

    def test_replace_all(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        (tmp_workspace / "dupes.txt").write_text("aaa bbb aaa ccc aaa")
        result = self.tool.execute(
            {
                "path": "dupes.txt",
                "old_text": "aaa",
                "new_text": "xxx",
                "replace_all": True,
            },
            tool_ctx,
        )
        assert result.status == "ok"
        content = (tmp_workspace / "dupes.txt").read_text()
        assert content == "xxx bbb xxx ccc xxx"

    def test_file_not_found(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute(
            {"path": "missing.txt", "old_text": "a", "new_text": "b"},
            tool_ctx,
        )
        assert result.status == "error"

    def test_sandbox_violation(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute(
            {"path": "../../etc/passwd", "old_text": "root", "new_text": "hacked"},
            tool_ctx,
        )
        assert result.status == "error"

    def test_missing_old_text(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute(
            {"path": "hello.txt", "old_text": "", "new_text": "x"},
            tool_ctx,
        )
        assert result.status == "error"
