"""AgentRunner: the send-execute-repeat loop."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from lcc.agent.context import ContextManager
from lcc.agent.messages import (
    ChatRequest,
    ConversationState,
    ToolCall,
)
from lcc.agent.prompts import build_system_prompt, format_tool_descriptions
from lcc.tools.base import ToolExecutionContext, ToolResult
from lcc.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
IDENTICAL_CALL_THRESHOLD = 3


@dataclass
class AgentTurnResult:
    """Result of a single agent turn (may span multiple iterations)."""

    final_text: str | None = None
    tool_results: list[ToolResult] = field(default_factory=list)
    iterations: int = 0
    stopped_reason: str | None = None


class AgentRunner:
    """Runs the agent loop: send to provider, execute tools, repeat.

    Handles tool dispatch, JSON recovery, infinite-loop detection,
    and context trimming.
    """

    def __init__(
        self,
        provider: Any,  # ChatProvider (duck-typed)
        registry: ToolRegistry,
        context_manager: ContextManager,
        conversation: ConversationState,
        tool_context: ToolExecutionContext,
        model: str = "",
        max_tokens: int | None = None,
        max_iterations: int = MAX_ITERATIONS,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._context_mgr = context_manager
        self._conversation = conversation
        self._tool_ctx = tool_context
        self._model = model
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations
        self._system_prompt_set = False

    @property
    def conversation(self) -> ConversationState:
        return self._conversation

    def _ensure_system_prompt(self) -> None:
        """Set the system prompt if not already done."""
        if self._system_prompt_set:
            return
        schemas = self._registry.openai_schemas()
        tool_desc = format_tool_descriptions(schemas)
        prompt = build_system_prompt(
            tool_descriptions=tool_desc,
            workspace_root=str(self._tool_ctx.sandbox.root),
        )
        self._conversation.append_system(prompt)
        self._system_prompt_set = True

    def run_turn(self, user_input: str) -> AgentTurnResult:
        """Run one user turn through the agent loop.

        Appends the user message, sends to the provider, executes any
        tool calls, and repeats until the model returns a text-only
        response or max_iterations is reached.
        """
        self._ensure_system_prompt()
        self._conversation.append_user(user_input)

        result = AgentTurnResult()
        recent_calls: list[str] = []

        for iteration in range(self._max_iterations):
            result.iterations = iteration + 1

            # Trim context to budget
            trimmed = self._context_mgr.trim(self._conversation.messages)

            # Build request
            request = ChatRequest(
                messages=[m.to_api_dict() for m in trimmed],
                tools=self._registry.openai_schemas() or None,
                model=self._model,
                max_tokens=self._max_tokens,
            )

            # Call provider
            try:
                response = self._provider.complete(request)
            except Exception as exc:
                logger.error("Provider error: %s", exc)
                result.final_text = f"Error communicating with the model: {exc}"
                result.stopped_reason = "provider_error"
                return result

            # Check for text-only response (no tool calls)
            if not response.tool_calls:
                self._conversation.append_assistant(response.content)
                result.final_text = response.content
                result.stopped_reason = "natural"
                return result

            # Process tool calls
            self._conversation.append_assistant(response.content, response.tool_calls)

            # Infinite loop detection
            call_signature = _serialize_tool_calls(response.tool_calls)
            recent_calls.append(call_signature)
            if _detect_infinite_loop(recent_calls, IDENTICAL_CALL_THRESHOLD):
                msg = (
                    "Detected repeated identical tool calls. "
                    "Stopping to prevent infinite loop."
                )
                self._conversation.append_user(msg)
                result.final_text = msg
                result.stopped_reason = "infinite_loop"
                return result

            # Execute each tool call
            tool_results = self._execute_tool_calls(response.tool_calls)
            result.tool_results.extend(tool_results)

        # Max iterations reached
        msg = f"Reached maximum iterations ({self._max_iterations}). Stopping."
        result.final_text = msg
        result.stopped_reason = "max_iterations"
        return result

    def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute a list of tool calls and append results to conversation."""
        results: list[ToolResult] = []
        for tc in tool_calls:
            args_json = (
                json.dumps(tc.arguments)
                if isinstance(tc.arguments, dict)
                else str(tc.arguments)
            )
            tool_result = self._registry.execute_tool_call(
                tc.name, args_json, self._tool_ctx
            )
            self._conversation.append_tool_result(tc.id, tool_result.output)
            results.append(tool_result)
        return results


def _serialize_tool_calls(tool_calls: list[ToolCall]) -> str:
    """Create a deterministic string representation of tool calls for comparison."""
    parts: list[str] = []
    for tc in tool_calls:
        args_str = json.dumps(tc.arguments, sort_keys=True)
        parts.append(f"{tc.name}:{args_str}")
    return "|".join(sorted(parts))


def _detect_infinite_loop(
    recent_signatures: list[str],
    threshold: int,
) -> bool:
    """Detect if the last N call signatures are identical."""
    if len(recent_signatures) < threshold:
        return False
    last_n = recent_signatures[-threshold:]
    return len(set(last_n)) == 1
