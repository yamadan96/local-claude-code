"""Tests for the agent loop with MockProvider."""

from __future__ import annotations

from pathlib import Path

from lcc.agent.context import ContextManager
from lcc.agent.loop import AgentRunner
from lcc.agent.messages import ChatResponse, ConversationState, ToolCall
from lcc.providers.mock import MockProvider
from lcc.safety.permissions import PermissionManager, PermissionMode, auto_approve
from lcc.safety.sandbox import WorkspaceSandbox
from lcc.tools.base import ToolExecutionContext
from lcc.tools.fs_read import ReadFileTool
from lcc.tools.registry import ToolRegistry


def _make_runner(
    responses: list[ChatResponse],
    workspace: Path,
    max_iterations: int = 10,
) -> AgentRunner:
    """Helper to create an AgentRunner with a MockProvider."""
    provider = MockProvider(responses)
    registry = ToolRegistry()
    registry.register(ReadFileTool())

    sandbox = WorkspaceSandbox(workspace)
    permissions = PermissionManager(mode=PermissionMode.AUTO, prompt_fn=auto_approve)
    tool_ctx = ToolExecutionContext(sandbox=sandbox, permissions=permissions)
    conversation = ConversationState()
    context_mgr = ContextManager(max_input_tokens=16000)

    return AgentRunner(
        provider=provider,
        registry=registry,
        context_manager=context_mgr,
        conversation=conversation,
        tool_context=tool_ctx,
        model="test-model",
        max_iterations=max_iterations,
    )


class TestAgentLoop:
    def test_simple_text_response(self, tmp_path: Path) -> None:
        """Model returns plain text, no tool calls."""
        responses = [
            ChatResponse(content="Hello! I'm here to help."),
        ]
        runner = _make_runner(responses, tmp_path)
        result = runner.run_turn("Hi")
        assert result.final_text == "Hello! I'm here to help."
        assert result.stopped_reason == "natural"
        assert result.iterations == 1

    def test_tool_call_then_text(self, tmp_path: Path) -> None:
        """Model calls a tool, gets result, then returns text."""
        (tmp_path / "test.txt").write_text("file contents here\n")
        responses = [
            # First: model requests to read a file
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="read_file",
                        arguments={"path": "test.txt"},
                    )
                ],
            ),
            # Second: model returns final text after seeing tool result
            ChatResponse(content="The file contains: file contents here"),
        ]
        runner = _make_runner(responses, tmp_path)
        result = runner.run_turn("Read test.txt")
        assert result.final_text == "The file contains: file contents here"
        assert result.stopped_reason == "natural"
        assert result.iterations == 2
        assert len(result.tool_results) == 1
        assert result.tool_results[0].status == "ok"

    def test_unknown_tool_handled(self, tmp_path: Path) -> None:
        """Model calls a non-existent tool; error result sent back."""
        responses = [
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(id="call_1", name="nonexistent_tool", arguments={})
                ],
            ),
            ChatResponse(content="Sorry, that tool doesn't exist."),
        ]
        runner = _make_runner(responses, tmp_path)
        result = runner.run_turn("Do something")
        assert result.final_text == "Sorry, that tool doesn't exist."
        assert len(result.tool_results) == 1
        assert result.tool_results[0].status == "error"
        assert "Unknown tool" in result.tool_results[0].output

    def test_max_iterations_reached(self, tmp_path: Path) -> None:
        """Agent should stop after max_iterations."""
        # Each iteration uses a different file to avoid infinite-loop detection
        responses = [
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id=f"call_{i}",
                        name="read_file",
                        arguments={"path": f"file_{i}.txt"},
                    )
                ],
            )
            for i in range(5)
        ]
        runner = _make_runner(responses, tmp_path, max_iterations=3)
        result = runner.run_turn("loop forever")
        assert result.stopped_reason == "max_iterations"
        assert "maximum iterations" in result.final_text.lower()

    def test_infinite_loop_detection(self, tmp_path: Path) -> None:
        """Detect 3 consecutive identical tool calls."""
        (tmp_path / "x.txt").write_text("x")
        identical_tc = ToolCall(
            id="call_same", name="read_file", arguments={"path": "x.txt"}
        )
        responses = [
            ChatResponse(content=None, tool_calls=[identical_tc]),
            ChatResponse(content=None, tool_calls=[identical_tc]),
            ChatResponse(content=None, tool_calls=[identical_tc]),
            ChatResponse(content="Should not reach here"),
        ]
        runner = _make_runner(responses, tmp_path)
        result = runner.run_turn("infinite loop")
        assert result.stopped_reason == "infinite_loop"
        assert (
            "repeated" in result.final_text.lower()
            or "infinite" in result.final_text.lower()
        )

    def test_tool_error_continues_loop(self, tmp_path: Path) -> None:
        """Tool returning an error should not crash the loop."""
        responses = [
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="read_file",
                        arguments={"path": "doesnt_exist.txt"},
                    )
                ],
            ),
            ChatResponse(content="File not found, sorry."),
        ]
        runner = _make_runner(responses, tmp_path)
        result = runner.run_turn("read a missing file")
        assert result.final_text == "File not found, sorry."
        assert result.tool_results[0].status == "error"

    def test_provider_error_handled(self, tmp_path: Path) -> None:
        """Provider exception should be caught and reported."""
        provider = MockProvider([])  # No responses = will raise
        registry = ToolRegistry()
        sandbox = WorkspaceSandbox(tmp_path)
        permissions = PermissionManager(mode=PermissionMode.AUTO)
        tool_ctx = ToolExecutionContext(sandbox=sandbox, permissions=permissions)
        conversation = ConversationState()
        context_mgr = ContextManager(max_input_tokens=16000)

        runner = AgentRunner(
            provider=provider,
            registry=registry,
            context_manager=context_mgr,
            conversation=conversation,
            tool_context=tool_ctx,
            model="test",
        )
        result = runner.run_turn("hello")
        assert result.stopped_reason == "provider_error"
        assert "error" in result.final_text.lower()

    def test_conversation_state_preserved(self, tmp_path: Path) -> None:
        """Messages should accumulate across turns."""
        responses = [
            ChatResponse(content="Answer 1"),
            ChatResponse(content="Answer 2"),
        ]
        runner = _make_runner(responses, tmp_path)
        runner.run_turn("Question 1")
        runner.run_turn("Question 2")
        msgs = runner.conversation.messages
        user_msgs = [m for m in msgs if m.role == "user"]
        assert len(user_msgs) == 2


class TestE2ESmokeTest:
    """End-to-end smoke test: scripted MockProvider conversation
    where the agent reads a file and answers."""

    def test_read_file_and_answer(self, tmp_path: Path) -> None:
        # Create a file to be read
        (tmp_path / "readme.md").write_text("# My Project\nThis is a test project.\n")

        responses = [
            # Model decides to read the file
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="tc_1",
                        name="read_file",
                        arguments={"path": "readme.md"},
                    )
                ],
            ),
            # Model generates final answer based on file content
            ChatResponse(content="The README describes 'My Project' - a test project."),
        ]

        runner = _make_runner(responses, tmp_path)
        result = runner.run_turn("What does the README say?")

        # Verify the full flow
        assert result.stopped_reason == "natural"
        assert (
            result.final_text == "The README describes 'My Project' - a test project."
        )
        assert result.iterations == 2
        assert len(result.tool_results) == 1
        assert result.tool_results[0].status == "ok"
        assert "My Project" in result.tool_results[0].output

        # Verify conversation state
        msgs = runner.conversation.messages
        roles = [m.role for m in msgs]
        assert roles[0] == "system"
        assert roles[1] == "user"
        assert roles[2] == "assistant"  # tool call
        assert roles[3] == "tool"  # tool result
        assert roles[4] == "assistant"  # final answer
