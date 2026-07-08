"""Tests for bash tool."""

from __future__ import annotations

from lcc.tools.base import ToolExecutionContext
from lcc.tools.shell import BashTool


class TestBashTool:
    def setup_method(self) -> None:
        self.tool = BashTool()

    def test_name(self) -> None:
        assert self.tool.name == "bash"

    def test_successful_command(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"command": "echo hello"}, tool_ctx)
        assert result.status == "ok"
        assert "hello" in result.output

    def test_nonzero_exit_code(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"command": "exit 1"}, tool_ctx)
        assert result.status == "error"
        assert "exit code 1" in result.output

    def test_stderr_output(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"command": "echo err >&2"}, tool_ctx)
        assert "stderr" in result.output.lower() or "err" in result.output

    def test_timeout(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute(
            {"command": "sleep 10", "timeout_seconds": 1}, tool_ctx
        )
        assert result.status == "error"
        assert "timed out" in result.output.lower()

    def test_missing_command(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({}, tool_ctx)
        assert result.status == "error"

    def test_cwd_is_workspace_root(self, tool_ctx: ToolExecutionContext) -> None:
        result = self.tool.execute({"command": "pwd"}, tool_ctx)
        assert result.status == "ok"
        assert str(tool_ctx.sandbox.root) in result.output

    def test_permission_denied_via_registry(
        self, tool_ctx_deny: ToolExecutionContext
    ) -> None:
        """bash is a privileged tool and should be denied."""
        from lcc.tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register(self.tool)
        result = registry.execute_tool_call(
            "bash", '{"command": "echo hi"}', tool_ctx_deny
        )
        assert result.status == "error"
        assert "denied" in result.output.lower()
