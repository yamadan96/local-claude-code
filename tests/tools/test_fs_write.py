"""Tests for write_file tool."""

from __future__ import annotations

from pathlib import Path

from lcc.tools.base import ToolExecutionContext
from lcc.tools.fs_write import WriteFileTool


class TestWriteFileTool:
    def setup_method(self) -> None:
        self.tool = WriteFileTool()

    def test_name(self) -> None:
        assert self.tool.name == "write_file"

    def test_write_new_file(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        result = self.tool.execute(
            {"path": "new_file.txt", "content": "new content"}, tool_ctx
        )
        assert result.status == "ok"
        assert (tmp_workspace / "new_file.txt").read_text() == "new content"

    def test_overwrite_existing_file(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        result = self.tool.execute(
            {"path": "hello.txt", "content": "overwritten"}, tool_ctx
        )
        assert result.status == "ok"
        assert (tmp_workspace / "hello.txt").read_text() == "overwritten"

    def test_create_parent_directories(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        result = self.tool.execute(
            {"path": "deep/nested/dir/file.txt", "content": "deep content"},
            tool_ctx,
        )
        assert result.status == "ok"
        assert (
            tmp_workspace / "deep" / "nested" / "dir" / "file.txt"
        ).read_text() == "deep content"

    def test_missing_path(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"content": "no path"}, tool_ctx)
        assert result.status == "error"

    def test_missing_content(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "file.txt"}, tool_ctx)
        assert result.status == "error"

    def test_sandbox_violation(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute(
            {"path": "../../escape.txt", "content": "evil"},
            tool_ctx,
        )
        assert result.status == "error"

    def test_permission_denied_in_ask_mode(
        self, tool_ctx_deny: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        """write_file is a privileged tool and should be denied by the deny fixture."""
        from lcc.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(self.tool)
        result = registry.execute_tool_call(
            "write_file",
            '{"path": "test.txt", "content": "denied"}',
            tool_ctx_deny,
        )
        assert result.status == "error"
        assert "denied" in result.output.lower()
