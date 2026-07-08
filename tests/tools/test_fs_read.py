"""Tests for read_file tool."""

from __future__ import annotations

from pathlib import Path

from lcc.tools.base import ToolExecutionContext
from lcc.tools.fs_read import ReadFileTool


class TestReadFileTool:
    def setup_method(self) -> None:
        self.tool = ReadFileTool()

    def test_name(self) -> None:
        assert self.tool.name == "read_file"

    def test_schema_has_required_fields(self) -> None:
        schema = self.tool.schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "read_file"
        assert "path" in schema["function"]["parameters"]["properties"]

    def test_read_entire_file(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        result = self.tool.execute({"path": "hello.txt"}, tool_ctx)
        assert result.status == "ok"
        assert "Hello, World!" in result.output
        assert "Line 2" in result.output

    def test_read_with_line_range(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        result = self.tool.execute(
            {"path": "hello.txt", "start_line": 2, "end_line": 2}, tool_ctx
        )
        assert result.status == "ok"
        assert "Line 2" in result.output
        assert "Hello, World!" not in result.output

    def test_read_missing_file(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "nonexistent.txt"}, tool_ctx)
        assert result.status == "error"
        assert "not found" in result.output.lower() or "File not found" in result.output

    def test_read_directory_not_file(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "subdir"}, tool_ctx)
        assert result.status == "error"
        assert "Not a file" in result.output

    def test_read_binary_file(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        (tmp_workspace / "binary.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
        result = self.tool.execute({"path": "binary.bin"}, tool_ctx)
        assert result.status == "error"
        assert "binary" in result.output.lower()

    def test_sandbox_violation_parent_traversal(
        self, tool_ctx: ToolExecutionContext
    ) -> None:
        result = self.tool.execute({"path": "../../etc/passwd"}, tool_ctx)
        assert result.status == "error"
        assert "outside" in result.output.lower() or "denied" in result.output.lower()

    def test_sandbox_violation_absolute_path(
        self, tool_ctx: ToolExecutionContext
    ) -> None:
        result = self.tool.execute({"path": "/etc/passwd"}, tool_ctx)
        assert result.status == "error"

    def test_missing_path_argument(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({}, tool_ctx)
        assert result.status == "error"
        assert "path" in result.output.lower()

    def test_read_nested_file(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "subdir/nested.txt"}, tool_ctx)
        assert result.status == "ok"
        assert "nested content" in result.output

    def test_line_numbers_in_output(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"path": "hello.txt"}, tool_ctx)
        assert result.status == "ok"
        assert "1\t" in result.output

    def test_symlink_escape(
        self, tool_ctx: ToolExecutionContext, tmp_workspace: Path
    ) -> None:
        """Symlink inside workspace pointing outside should be rejected."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"secret")
            external_path = Path(f.name)

        try:
            link_path = tmp_workspace / "sneaky_link.txt"
            link_path.symlink_to(external_path)
            result = self.tool.execute({"path": "sneaky_link.txt"}, tool_ctx)
            assert result.status == "error"
        finally:
            external_path.unlink(missing_ok=True)
